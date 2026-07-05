# Assistant documentaire Lite RAG

Mini-application IA (RAG — *Retrieval-Augmented Generation*) capable de répondre à
des questions **à partir d'un document fourni** (discours de Barack Obama, 2013).
L'assistant ne se comporte pas comme un chatbot généraliste : il répond en
s'appuyant sur les passages retrouvés dans le document, et indique clairement
lorsqu'une information n'y figure pas.

> Projet réalisé dans le cadre de l'évaluation pratique finale du module Cloud
> (École Hexagone).

---

## Principe RAG

```
Document → Découpage → Embeddings → Base vectorielle → Recherche
        → Prompt enrichi → Réponse + sources
```

| Étape | Rôle |
|-------|------|
| **Document source** | Corpus de travail (`data/corpus_de_travail.txt`) |
| **Découpage** | Coupe le texte en passages courts (chunks) |
| **Embeddings** | Transforme chaque passage en vecteur numérique |
| **Base vectorielle** | Stocke les vecteurs et permet la recherche par similarité |
| **Recherche** | Récupère les `top_k` passages proches de la question |
| **Prompt enrichi** | Construit un prompt = consigne + contexte + question |
| **LLM** | Génère la réponse à partir du seul contexte fourni |

---

## Stack technique

| Besoin | Outil |
|--------|-------|
| Interface utilisateur | **Next.js / React / MUI** (façon NotebookLM) |
| Backend API | **FastAPI** |
| Stockage du document brut | **MinIO** (S3-compatible) |
| Base vectorielle | **ChromaDB** |
| Orchestration RAG | **LangChain** |
| Modèle d'embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| LLM local | **Ollama** — `gemma3` (~4B) |
| Retrieval avancé | Hybrid (dense + **BM25**/RRF) · **MMR** · **reranking** cross-encoder · reorder |
| CI | **GitHub Actions** |

---

## Arborescence

Le projet est organisé en **3 dépôts git** : un dépôt parent (orchestration) qui
référence `backend` et `frontend` comme **submodules git** (voir plus bas).

```
eval_cloud/                    # Dépôt parent (orchestration)
├── docker-compose.yml        # Orchestration des 5 services
├── .env.example              # Variables d'environnement (à copier en .env)
├── .gitmodules               # Déclaration des submodules backend / frontend
├── data/
│   └── corpus_de_travail.txt # Document source fourni
├── backend/                  # ⟶ submodule : eval_cloud-backend
│   ├── Dockerfile            #   API FastAPI + chaîne RAG (LangChain)
│   ├── requirements.txt
│   ├── main.py               #   Point d'entrée FastAPI
│   ├── app/
│   │   ├── config.py         #   Configuration (variables d'env)
│   │   ├── api/routes.py     #   Endpoints : /health /upload /index /ask
│   │   ├── rag/              #   chunking, embeddings, vectorstore, prompt, pipeline
│   │   └── storage/          #   client MinIO
│   └── tests/                #   tests unitaires (chunking, prompt, /health)
├── frontend/                 # ⟶ submodule : eval_cloud-frontend (Next.js)
│   ├── Dockerfile            #   Interface Next.js (façon NotebookLM)
│   ├── package.json
│   ├── app/                  #   App Router (layout, page, providers)
│   ├── components/           #   layout / sources / chat / studio
│   ├── lib/ hooks/ stores/   #   client API, hooks Query, état Zustand
├── scripts/                  # scripts utilitaires (Ollama, push submodules)
└── .github/workflows/ci.yml  # CI GitHub Actions
```

### Structure en submodules

`backend/` et `frontend/` sont des dépôts GitHub **distincts**, référencés par le
dépôt parent à un commit précis :

| Dépôt | Rôle |
| ----- | ---- |
| `Dorsumsellae/eval_cloud` | Parent : orchestration (docker-compose, data, CI) |
| `Dorsumsellae/eval_cloud-backend` | Submodule `backend/` (FastAPI + RAG) |
| `Dorsumsellae/eval_cloud-frontend` | Submodule `frontend/` (Next.js) |

**Cloner le projet complet** (submodules inclus) :

```bash
git clone --recursive https://github.com/Dorsumsellae/eval_cloud.git
# ou, après un clone simple :
git submodule update --init --recursive
```

**Publier les submodules sur GitHub** (une fois `gh` installé et authentifié) :

```bash
bash scripts/push_submodules.sh
```

Ce script crée les dépôts `eval_cloud-backend` / `eval_cloud-frontend`, les pousse,
puis pousse le commit de conversion du dépôt parent.

> Workflow submodules : un changement dans `backend/` ou `frontend/` se commite
> **dans le submodule** (`cd backend && git commit && git push`), puis le nouveau
> pointeur se commite **dans le parent** (`git add backend && git commit`).

---

## Lancer l'application

### Option A — Docker Compose (recommandé)

```bash
cp .env.example .env
docker compose up --build
```

Au premier démarrage, le service `ollama-pull` télécharge automatiquement le
modèle `gemma3` (~3 Go ; cela peut prendre plusieurs minutes).

| Service | URL |
|---------|-----|
| Interface Next.js | http://localhost:3000 |
| API FastAPI (docs) | http://localhost:8000/docs |
| Console MinIO | http://localhost:9001 |

> L'interface (client navigateur) appelle le backend via `NEXT_PUBLIC_API_BASE_URL`
> (défaut `http://localhost:8000`, inliné au build du frontend). Le CORS du backend
> est ouvert, l'appel cross-origin fonctionne donc directement.

#### Accélération GPU (selon le matériel)

Par défaut, Ollama tourne en **CPU** (fonctionne partout). Pour exploiter un GPU,
on ajoute un fichier d'override au lancement selon la machine :

| Matériel | Commande |
|----------|----------|
| **CPU** (défaut) | `docker compose up --build` |
| **GPU NVIDIA** (Linux ou Windows/WSL2) | `docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up --build` |
| **GPU AMD / ROCm** (Linux **uniquement**) | `docker compose -f docker-compose.yml -f docker-compose.amd.yml up --build` |
| **Ollama natif sur l'hôte** (ex. GPU AMD sous Windows) | voir ci-dessous |

- **NVIDIA** nécessite le *NVIDIA Container Toolkit* sur l'hôte. Vérification :
  `docker exec rag-ollama nvidia-smi`.
- **AMD/ROCm** utilise l'image `ollama/ollama:rocm` et n'est **pas** disponible dans
  Docker Desktop / WSL2 sous Windows (ROCm y est inaccessible). Vérification :
  `docker exec rag-ollama rocminfo`.
- **Ollama natif sur l'hôte** : le backend (en container) se connecte à un Ollama
  installé directement sur la machine — seule option pour un **GPU AMD sous Windows**.
  Ollama doit écouter sur `0.0.0.0` (variable d'hôte `OLLAMA_HOST=0.0.0.0`) :

  ```bash
  cp .env.host-ollama.example .env
  docker compose -f docker-compose.yml -f docker-compose.host-ollama.yml up --build
  ```

  Cet override range les services `ollama` / `ollama-pull` embarqués dans un profil
  et pointe `OLLAMA_BASE_URL` vers `http://host.docker.internal:11434`
  (voir les prérequis détaillés dans `.env.host-ollama.example`).

### Option B — Lancement local (sans Docker)

Backend : `pip install -r backend/requirements.txt` puis, dans `backend/`,
`uvicorn main:app --reload`. Frontend : `cd frontend && npm install && npm run dev`
(sert l'interface sur http://localhost:3000). Il faut aussi installer et lancer
Ollama manuellement :

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull gemma3
```

---

## Utilisation

Interface **façon NotebookLM** en 3 panneaux : **Sources** (gauche), **Chat**
(centre), **Studio** (droite).

1. Ouvrir l'interface Next.js (http://localhost:3000).
2. Choisir ou créer un **Notebook** (barre du haut).
3. **Ajouter des sources** (panneau de gauche) : fichier (`.txt`, `.pdf`, `.md`,
   `.srt`, `.vtt`) ou vidéo YouTube. L'indexation est automatique.
4. Cocher éventuellement un **sous-ensemble de sources** pour cibler la recherche.
5. **Discuter** dans le panneau central : la conversation garde la mémoire des
   échanges, et les réponses citent les passages via des puces `[n]` cliquables
   (extrait, locuteur, lien horodaté pour les vidéos).

### Exemples de questions

- Quelles priorités économiques sont évoquées dans le discours ?
- Que dit le texte sur l'éducation ?
- Que propose le discours concernant le salaire minimum ?

---

## Endpoints de l'API

| Méthode | Endpoint | Rôle |
|---------|----------|------|
| `GET` | `/health` | Vérification de disponibilité |
| `POST` | `/upload` | Envoi du document (stockage MinIO), rangé par workspace |
| `POST` | `/index` | Indexation (texte, PDF, ou **transcript horodaté**) |
| `POST` | `/ingest/youtube` | Récupère les sous-titres d'une vidéo YouTube et les indexe |
| `GET` | `/documents` | Liste des documents indexés d'un workspace (`?workspace=…`) |
| `GET` | `/workspaces` | Liste des workspaces existants |
| `POST` | `/ask` | Question → réponse + sources (cloisonnée ; sous-ensemble via `filenames`) |
| `POST` | `/chat` | Conversation **multi-tours** → réponse + sources + citations `[n]` |
| `POST` | `/reset` | Réinitialise un workspace (entier, ou un seul document) |

### Transcripts & YouTube

L'assistant gère les **transcripts horodatés**, en plus du texte et des PDF :

- **Formats** : `.srt`, `.vtt`, et `.txt` au format `[HH:MM:SS] texte` (export type
  YouTube). Le format est détecté automatiquement à l'indexation.
- **Nettoyage** : retrait des annotations non verbales (`[rires]`, `[musique]`) et
  des balises de sous-titrage (`<c>`, `<00:00:00.000>`), lignes fragmentées fusionnées.
- **Découpage temporel** : les passages respectent les frontières de segments et
  conservent leur instant (`start`/`end`), au lieu d'un découpage aveugle au caractère.
- **Sources cliquables** : pour un transcript YouTube, chaque source renvoie
  `start_seconds` et un `timecode_url` (`…&t=<secondes>s`) pointant vers l'instant
  exact de la vidéo.

Import direct depuis une URL (récupération automatique des sous-titres) :

```bash
curl -X POST http://localhost:8000/ingest/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "workspace": "ma-video", "languages": ["fr", "en"]}'
```

> Contrairement au reste de la stack (offline), cet endpoint nécessite un **accès
> réseau sortant** vers YouTube. On peut aussi charger un fichier `.srt`/`.vtt` via
> `/upload` pour rester 100 % hors-ligne.

#### Vidéos sans sous-titres → transcription audio (ASR)

Quand une vidéo **n'a aucun sous-titre**, `/ingest/youtube` bascule automatiquement
sur un **service ASR isolé** (`asr/`) qui télécharge l'audio (`yt-dlp`) et le
transcrit avec **WhisperX** — avec **diarisation** (séparation des locuteurs) via
pyannote. Chaque passage porte alors son locuteur (`SPEAKER_00`, …), exploité dans
la recherche et l'affichage des sources.

Ce service est **isolé dans son propre conteneur** car WhisperX épingle
`torch`/`transformers` à des versions incompatibles avec la stack RAG : on évite
ainsi de dégrader les embeddings. Il est **optionnel** (profil `asr`) car lourd :

```bash
# .env : décommenter ASR_SERVICE_URL=http://asr:8100  (+ HF_TOKEN pour la diarisation)
docker compose --profile asr up --build          # ou -f ... -f docker-compose.host-ollama.yml
```

| Point | Détail |
|-------|--------|
| **Activation** | `ASR_SERVICE_URL` dans `.env` **et** profil `asr` au lancement |
| **Diarisation** | nécessite `HF_TOKEN` (whisperx charge `pyannote/speaker-diarization-community-1` ; accepter ses conditions sur huggingface.co si demandé). Sans jeton : transcription **sans** locuteurs (dégradation gracieuse) |
| **Langue** | Whisper détecte la langue parlée (= langue originale) |
| **Locuteurs** | `num_speakers` optimise : `1` = mono-locuteur → diarisation **ignorée** (plus rapide) ; `>1` = contrainte passée à pyannote ; absent = détection auto |
| **Perf** | lent sur CPU ; les vidéos longues peuvent dépasser le timeout HTTP (`ASR_TIMEOUT`) |

### Workspaces

Les documents sont **cloisonnés par _workspace_** (espace de travail) : une même
collection ChromaDB, mais chaque passage porte une métadonnée `workspace` sur
laquelle la recherche est filtrée. Concrètement :

- un `/ask` ne remonte **que** les passages du workspace ciblé — jamais ceux d'un
  autre espace (corrige un ancien comportement où la recherche était globale) ;
- deux workspaces peuvent contenir un fichier de même nom sans collision
  (clé MinIO `{workspace}/{filename}`, id ChromaDB `{workspace}:{filename}:{n}`) ;
- `workspace` est optionnel partout : sans valeur, `DEFAULT_WORKSPACE` (défaut
  `default`) est utilisé.

Côté UI, un workspace est présenté comme un **Notebook** : le sélecteur est dans
la barre du haut ; on en crée un nouveau en y ajoutant une première source.

### `GET /documents`

Renvoie les documents actuellement indexés dans ChromaDB, regroupés par nom de
fichier et triés par ordre alphabétique. Aucun paramètre. Si rien n'est indexé,
la réponse est `200 OK` avec une liste vide (jamais une erreur).

```json
{
  "documents": [
    { "filename": "corpus_de_travail.txt", "chunks_indexed": 12 }
  ],
  "count": 1
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `documents[].filename` | `string` | Nom du document indexé |
| `documents[].chunks_indexed` | `integer` | Nombre de passages (chunks) indexés pour ce document |
| `count` | `integer` | Nombre de documents distincts (= `documents.length`) |

---

## Tests & CI

```bash
cd backend && pytest
```

La CI (GitHub Actions) installe les dépendances et exécute les tests à chaque
push : découpage en chunks, construction du prompt, endpoint `/health`.

---

## Limites connues

- Temps de réponse parfois long (petit modèle local).
- Recherche hybride (BM25) : index reconstruit à la volée sur le périmètre — adapté
  à un corpus petit/moyen, pas à un très gros volume.
- Le reranker (cross-encoder, ~120 Mo) se télécharge au premier appel (mise en cache).
- Cloisonnement des workspaces **logique** (métadonnée filtrée), pas physique :
  pas d'authentification, un appelant peut cibler n'importe quel workspace.
- Le `/reset` d'un workspace vide ChromaDB mais laisse les objets bruts dans MinIO.
- Pas de monitoring avancé.
- Version de démonstration, non destinée à la production.

> **Principe respecté :** l'assistant répond à partir du document. S'il ne trouve
> pas l'information, il l'indique clairement.
