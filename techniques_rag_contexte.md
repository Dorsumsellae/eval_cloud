# Techniques d'optimisation du contexte d'un RAG

Le « contexte » d'un RAG se travaille à **plusieurs étapes** du pipeline, pas
seulement au moment du reranking. Panorama organisé par phase, avec à chaque
fois l'idée et l'intérêt.

> Rappel de la chaîne de base : `Document → Découpage → Embeddings → Base
> vectorielle → Recherche → Prompt enrichi → Réponse + sources`

---

## 1. Au découpage (chunking)

| Technique | Idée | Intérêt |
|---|---|---|
| **Fixed-size** | Couper tous les N caractères avec recouvrement | Simple (chunking de base) |
| **Recursive splitting** | Couper en respectant paragraphes → phrases → mots (`RecursiveCharacterTextSplitter`) | Évite de couper au milieu d'une phrase |
| **Semantic chunking** | Couper là où la similarité d'embeddings chute (changement de sujet) | Chunks cohérents sémantiquement |
| **Sentence-window / Small-to-Big** | Indexer de petits chunks, mais renvoyer au LLM une fenêtre élargie (voisins) | Recherche précise + contexte riche |
| **Hierarchical / Parent-document** | Indexer les enfants, retourner le parent | Précision à la recherche, contexte complet à la génération |

---

## 2. À l'enrichissement de l'index

- **Metadata enrichment** : ajouter titre, section, page, date → permet le
  **filtrage** ensuite.
- **Contextual Retrieval** (Anthropic) : préfixer chaque chunk d'un court résumé
  de sa place dans le document *avant* de l'embedder → réduit fortement les
  échecs de récupération.
- **Multi-vector / Summary indexing** : indexer un résumé (ou des questions
  générées) qui pointe vers le chunk complet.
- **HyDE** (*Hypothetical Document Embeddings*) : générer une réponse
  *hypothétique* à la question, puis chercher les chunks proches de cette
  réponse plutôt que de la question.

---

## 3. À la recherche (retrieval)

| Technique | Idée |
|---|---|
| **Dense retrieval** | Similarité vectorielle (embeddings) |
| **Sparse retrieval** | Recherche par mots-clés (BM25, TF-IDF) — imbattable sur les termes exacts, sigles, noms propres |
| **Hybrid search** | Combiner dense + sparse, fusionnés par **RRF** (*Reciprocal Rank Fusion*) |
| **MMR** (*Maximal Marginal Relevance*) | Pénaliser les passages redondants → diversité du contexte |
| **Multi-query / Query expansion** | Reformuler la question en plusieurs variantes, unir les résultats |
| **Query decomposition** | Découper une question complexe en sous-questions |
| **Self-query / Metadata filtering** | Extraire des filtres depuis la question (« en 2013 » → filtre date) |

---

## 4. Post-recherche — l'affinage du contexte (le **reranking**)

On récupère large (ex. `top_k=20`) puis on affine :

- **Reranking** ⭐ : un **cross-encoder** (ex. `bge-reranker`, `Cohere Rerank`,
  `ms-marco-MiniLM`) note finement chaque paire (question, passage) et réordonne.
  Plus précis que la similarité vectorielle brute (qui compare des vecteurs
  pré-calculés indépendamment). Pattern typique :
  *retrieve 20 → rerank → garder les 3-4 meilleurs*.
- **Contextual compression / extraction** : ne garder que les phrases
  pertinentes de chaque passage (LLM ou modèle d'extraction) → économise le
  contexte.
- **Déduplication** : retirer les passages quasi identiques.
- **Reordering « lost-in-the-middle »** : placer les passages les plus
  pertinents en **début et fin** du contexte (les LLM négligent le milieu).
- **Token budgeting** : tronquer/sélectionner pour tenir dans la fenêtre de
  contexte — **crucial avec un petit modèle** (ex. `qwen2.5:0.5b`).

---

## 5. À la génération (boucles correctives)

- **Self-RAG** : le modèle décide s'il faut récupérer, et critique ses propres
  réponses.
- **CRAG** (*Corrective RAG*) : évalue la qualité des passages ; si insuffisant,relance une recherche (ex. web).
- **Citations / grounding** : forcer le modèle à citer le passage source.

---

## Application au TP (Assistant documentaire Lite RAG)

La chaîne actuelle est le **socle standard** :
*chunking fixe → dense retrieval (ChromaDB) → `top_k=4` → prompt → LLM*.
C'est exactement ce qui est demandé.

Bonus réalistes et à fort effet, par rapport qualité/effort décroissant :

1. **MMR** (natif LangChain/Chroma : `search_type="mmr"`) — une ligne à changer.
2. **Reranking** avec un petit cross-encoder — le plus « impressionnant » à
   présenter, mais ajoute un modèle à charger.
3. **Recursive splitting** au lieu de la taille fixe — améliore la qualité des
   chunks sans coût.

> ⚠️ Avec un modèle aussi léger (0.5b) et une petite fenêtre de contexte, la
> **compression/sélection du contexte** apporte souvent plus que d'empiler des
> passages.
