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
| Interface utilisateur | **Streamlit** |
| Backend API | **FastAPI** |
| Stockage du document brut | **MinIO** (S3-compatible) |
| Base vectorielle | **ChromaDB** |
| Orchestration RAG | **LangChain** |
| Modèle d'embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| LLM local léger | **Ollama** — `qwen2.5:0.5b` |
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
├── frontend/                 # ⟶ submodule : eval_cloud-frontend
│   ├── Dockerfile            #   Interface Streamlit
│   ├── requirements.txt
│   └── app.py
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
| `Dorsumsellae/eval_cloud-frontend` | Submodule `frontend/` (Streamlit) |

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
modèle `qwen2.5:0.5b` (cela peut prendre quelques minutes).

| Service | URL |
|---------|-----|
| Interface Streamlit | http://localhost:8501 |
| API FastAPI (docs) | http://localhost:8000/docs |
| Console MinIO | http://localhost:9001 |

### Option B — Lancement local (sans Docker)

Voir les scripts dans [`scripts/`](scripts/) et les `requirements.txt` de chaque
service. Il faut installer et lancer Ollama manuellement :

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull qwen2.5:0.5b
```

---

## Utilisation

1. Ouvrir l'interface Streamlit.
2. **Charger / sélectionner** le document (`corpus_de_travail.txt`).
3. Lancer l'**indexation** (découpage → embeddings → ChromaDB).
4. **Poser une question** en langage naturel.
5. Lire la **réponse** et consulter les **sources** (nom du document, numéro de
   passage, extrait, score de similarité).

### Exemples de questions

- Quelles priorités économiques sont évoquées dans le discours ?
- Que dit le texte sur l'éducation ?
- Que propose le discours concernant le salaire minimum ?

---

## Endpoints de l'API

| Méthode | Endpoint | Rôle |
|---------|----------|------|
| `GET` | `/health` | Vérification de disponibilité |
| `POST` | `/upload` | Envoi du document (stockage MinIO) |
| `POST` | `/index` | Indexation du document dans ChromaDB |
| `POST` | `/ask` | Question → réponse + sources |

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
- Qualité imparfaite du modèle `qwen2.5:0.5b`.
- Corpus limité à un seul document.
- Pas d'authentification ni de monitoring avancé.
- Version de démonstration, non destinée à la production.

> **Principe respecté :** l'assistant répond à partir du document. S'il ne trouve
> pas l'information, il l'indique clairement.
