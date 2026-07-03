"""Interface Streamlit de l'assistant documentaire RAG."""

import os
import requests
import streamlit as st

# URL du backend FastAPI, configurable via variable d'environnement
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Configuration de la page Streamlit
st.set_page_config(page_title="Assistant documentaire RAG", page_icon="📄")
st.title("📄 Assistant documentaire Lite RAG")
st.caption("Répond à partir du document fourni — sinon il le dit clairement.")

# Initialisation des variables de session pour persister les données entre les interactions
if "filename" not in st.session_state:
    st.session_state.filename = None  # Nom du fichier sélectionné
if "indexed" not in st.session_state:
    st.session_state.indexed = False  # True si le document est indexé dans ChromaDB
if "historique" not in st.session_state:
    st.session_state.historique = []  # Liste des questions/réponses de la session
if "selected_model" not in st.session_state:
    st.session_state.selected_model = None  # Modèle Ollama sélectionné


def get_documents():
    """Récupère la liste des documents indexés dans ChromaDB via GET /documents."""
    try:
        resp = requests.get(f"{BACKEND_URL}/documents", timeout=10)
        resp.raise_for_status()
        return resp.json().get("documents", [])  # Retourne la liste ou [] si vide
    except requests.RequestException:
        return []  # Retourne liste vide si le backend est inaccessible


def get_models():
    """Récupère la liste des modèles Ollama disponibles via GET /models."""
    try:
        resp = requests.get(f"{BACKEND_URL}/models", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None  # Retourne None si Ollama est inaccessible


def reset_index(filename=None):
    """Réinitialise l'index ChromaDB.
    
    Si filename est fourni : supprime uniquement ce document.
    Si filename est None : supprime tout l'index.
    """
    try:
        body = {"filename": filename} if filename else {}  # Corps vide = reset complet
        resp = requests.post(f"{BACKEND_URL}/reset", json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# --- Barre laterale ---
with st.sidebar:
    st.header("1. Document")

    # Récupère les documents déjà indexés dans ChromaDB
    documents = get_documents()

    if documents:
        st.markdown("**Documents disponibles :**")
        noms = [d["filename"] for d in documents]  # Extrait uniquement les noms
        choix = st.selectbox("Sélectionner un document", noms)  # Menu déroulant

        # Bouton pour utiliser le document sélectionné sans réindexer
        if st.button("✅ Utiliser ce document"):
            st.session_state.filename = choix
            st.session_state.indexed = True  # Déjà indexé donc on passe directement à True
            st.success(f"Document sélectionné : {choix}")

        # Affiche le nombre de passages indexés pour le document choisi
        for d in documents:
            if d["filename"] == choix:
                st.caption(f"Passages indexés : {d['chunks_indexed']}")

        st.divider()

        # Section de gestion de l'index (masquée par défaut)
        with st.expander("🗑️ Gérer l'index"):
            # Supprime uniquement le document sélectionné
            if st.button("Supprimer ce document de l'index"):
                result = reset_index(filename=choix)
                if result:
                    chunks = result.get("chunks_removed", 0)
                    docs = result.get("documents_removed", 0)
                    st.success(f"Document supprimé — {docs} document(s) et {chunks} passages retirés de l'index")
                    st.session_state.filename = None
                    st.session_state.indexed = False
                    st.rerun()  # Recharge la page pour mettre à jour l'interface
                else:
                    st.error("Erreur lors de la suppression")

            # Réinitialise tout l'index ChromaDB
            if st.button("⚠️ Réinitialiser tout l'index"):
                result = reset_index()  # Pas de filename = reset complet
                if result:
                    chunks = result.get("chunks_removed", 0)
                    docs = result.get("documents_removed", 0)
                    st.success(f"Index réinitialisé — {docs} document(s) et {chunks} passages supprimés")
                    st.session_state.filename = None
                    st.session_state.indexed = False
                    st.rerun()
                else:
                    st.error("Erreur lors de la réinitialisation")
    else:
        # Aucun document indexé : invite l'utilisateur à en uploader un
        st.info("Aucun document indexé pour l'instant.")

    st.divider()

    # Section upload d'un nouveau document
    st.markdown("**Ajouter un document :**")
    uploaded = st.file_uploader("Charger un document (.txt)", type=["txt", "pdf"])

    # Bouton désactivé tant qu'aucun fichier n'est sélectionné
    if st.button("Envoyer le document", disabled=uploaded is None):
        with st.spinner("Envoi du document..."):
            try:
                # Envoie le fichier en multipart/form-data vers POST /upload
                files = {"file": (uploaded.name, uploaded.getvalue(), "text/plain")}
                resp = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
                resp.raise_for_status()
                st.session_state.filename = uploaded.name
                st.session_state.indexed = False  # Pas encore indexé
                st.success(f"Document envoyé : {uploaded.name}")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Erreur lors de l'envoi : {exc}")

    st.header("2. Indexation")

    # Affiche le fichier actuellement sélectionné
    if st.session_state.filename:
        st.info(f"Fichier actuel : {st.session_state.filename}")

    # Choix de la stratégie de découpage du texte en chunks
    strategy = st.radio(
        "Stratégie de découpage :",
        options=["fixed", "recursive"],
        index=0,  # "fixed" sélectionné par défaut
        help="fixed : découpage par taille fixe | recursive : découpage intelligent par paragraphes"
    )

    # Bouton désactivé si aucun fichier n'est sélectionné
    if st.button("Lancer l'indexation", disabled=st.session_state.filename is None):
        progress = st.progress(0, text="Démarrage de l'indexation...")
        try:
            progress.progress(20, text="Lecture du document...")
            # Envoie le nom du fichier et la stratégie choisie au backend
            resp = requests.post(
                f"{BACKEND_URL}/index",
                json={
                    "filename": st.session_state.filename,
                    "strategy": strategy  # "fixed" ou "recursive"
                },
                timeout=120  # Timeout long car l'indexation peut prendre du temps
            )
            progress.progress(60, text="Création des embeddings...")
            resp.raise_for_status()
            progress.progress(100, text="Indexation terminée !")
            data = resp.json()
            chunks = data.get("chunks_indexed", 0)  # Nombre de passages créés
            st.session_state.indexed = True
            st.success(f"✅ Indexation terminée — {chunks} passages créés avec la stratégie '{strategy}'")
            st.rerun()
        except requests.RequestException as exc:
            progress.empty()  # Supprime la barre de progression en cas d'erreur
            st.error(f"Erreur lors de l'indexation : {exc}")

    # Indicateur visuel si le document est indexé et prêt
    if st.session_state.indexed:
        st.success("✅ Document indexé — vous pouvez poser des questions")

    st.divider()
    st.header("🤖 Modèle")

    # Récupère les modèles Ollama disponibles sur le serveur
    models_data = get_models()
    if models_data:
        model_names = [m["name"] for m in models_data.get("models", [])]
        default_model = models_data.get("default")  # Modèle par défaut du serveur
        default_index = model_names.index(default_model) if default_model in model_names else 0

        # Menu déroulant pour choisir le modèle Ollama
        chosen_model = st.selectbox(
            "Modèle Ollama",
            options=model_names,
            index=default_index,
            help="Modèle utilisé pour générer la réponse. Défaut serveur si non modifié."
        )
        st.session_state.selected_model = chosen_model
    else:
        st.caption("⚠️ Impossible de récupérer la liste des modèles (serveur Ollama injoignable ?)")

    st.divider()
    st.header("📋 Historique")

    # Affiche l'historique des questions/réponses de la session
    if st.session_state.historique:
        if st.button("🗑️ Effacer l'historique"):
            st.session_state.historique = []
            st.rerun()
        # Affiche les questions les plus récentes en premier
        for i, item in enumerate(reversed(st.session_state.historique)):
            with st.expander(f"Q{len(st.session_state.historique) - i} : {item['question'][:40]}..."):
                st.write(item['answer'])
    else:
        st.caption("Aucune question posée pour l'instant.")

# --- Zone principale ---
st.header("3. Poser une question")

# Affiche un warning adapté selon l'état de la session
if not st.session_state.indexed:
    if not st.session_state.filename:
        st.warning("⚠️ Veuillez d'abord sélectionner ou charger un document.")
    else:
        st.warning("⚠️ Veuillez lancer l'indexation avant de poser une question.")

# Champ de saisie désactivé tant que le document n'est pas indexé
question = st.text_input(
    "Votre question",
    placeholder="Que dit le texte sur l'éducation ?",
    disabled=not st.session_state.indexed
)

# Bouton désactivé si pas de question ou document non indexé
if st.button("Interroger", type="primary", disabled=not question or not st.session_state.indexed):
    with st.spinner("Recherche et génération de la réponse..."):
        try:
            # Construction du payload avec la question et le modèle choisi
            payload = {"question": question}
            if st.session_state.selected_model:
                payload["model"] = st.session_state.selected_model  # Modèle optionnel

            # Appel POST /ask avec timeout long car Ollama peut être lent
            resp = requests.post(
                f"{BACKEND_URL}/ask",
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()

            # Affichage de la réponse générée par le LLM
            st.subheader("Réponse")
            st.write(data.get("answer", ""))

            # Affiche le modèle utilisé si renvoyé par le backend
            used_model = data.get("model")
            if used_model:
                st.caption(f"🤖 Modèle utilisé : {used_model}")

            # Compteur de passages trouvés dans ChromaDB
            sources = data.get("sources", [])
            st.info(f"🔍 {len(sources)} passage(s) trouvé(s) dans le document")

            # Affichage des sources avec le nom du fichier, le passage et le score
            st.subheader("Sources")
            if sources:
                for s in sources:
                    with st.expander(
                        f"📄 {s['filename']} — passage {s['passage_id']}"
                        + (f" (score {s['score']:.3f})" if s.get("score") is not None else "")
                    ):
                        st.write(s["excerpt"])  # Extrait du passage utilisé
            else:
                st.info("Aucune source trouvée.")

            # Sauvegarde la question et la réponse dans l'historique de session
            st.session_state.historique.append({
                "question": question,
                "answer": data.get("answer", "")
            })

        except requests.RequestException as exc:
            st.error(f"Erreur lors de l'appel au backend : {exc}")