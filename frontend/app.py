"""Interface Streamlit de l'assistant documentaire RAG."""

import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Assistant documentaire RAG", page_icon="📄")
st.title("📄 Assistant documentaire Lite RAG")
st.caption("Répond à partir du document fourni — sinon il le dit clairement.")

# Initialisation session state
if "filename" not in st.session_state:
    st.session_state.filename = None
if "indexed" not in st.session_state:
    st.session_state.indexed = False
if "historique" not in st.session_state:
    st.session_state.historique = []


def get_documents():
    """Récupère la liste des documents indexés via GET /documents."""
    try:
        resp = requests.get(f"{BACKEND_URL}/documents", timeout=10)
        resp.raise_for_status()
        return resp.json().get("documents", [])
    except requests.RequestException:
        return []


def reset_index(filename=None):
    """Réinitialise l'index complet ou un document précis."""
    try:
        body = {"filename": filename} if filename else {}
        resp = requests.post(f"{BACKEND_URL}/reset", json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# --- Barre laterale ---
with st.sidebar:
    st.header("1. Document")

    # Récupérer les documents disponibles dans ChromaDB
    documents = get_documents()

    if documents:
        st.markdown("**Documents disponibles :**")
        noms = [d["filename"] for d in documents]
        choix = st.selectbox("Sélectionner un document", noms)
        if st.button("✅ Utiliser ce document"):
            st.session_state.filename = choix
            st.session_state.indexed = True
            st.success(f"Document sélectionné : {choix}")

        # Infos sur le document sélectionné
        for d in documents:
            if d["filename"] == choix:
                st.caption(f"Passages indexés : {d['chunks_indexed']}")

        st.divider()

        # Reset
        with st.expander("🗑️ Gérer l'index"):
            if st.button("Supprimer ce document de l'index"):
                result = reset_index(filename=choix)
                if result:
                    chunks = result.get("chunks_removed", 0)
                    docs = result.get("documents_removed", 0)
                    st.success(f"Document supprimé — {docs} document(s) et {chunks} passages retirés de l'index")
                    st.session_state.filename = None
                    st.session_state.indexed = False
                    st.rerun()
                else:
                    st.error("Erreur lors de la suppression")

            if st.button("⚠️ Réinitialiser tout l'index"):
                result = reset_index()
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
        st.info("Aucun document indexé pour l'instant.")

    st.divider()

    # Upload d'un nouveau document
    st.markdown("**Ajouter un document :**")
    uploaded = st.file_uploader("Charger un document (.txt)", type=["txt", "pdf"])

    if st.button("Envoyer le document", disabled=uploaded is None):
        with st.spinner("Envoi du document..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), "text/plain")}
                resp = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
                resp.raise_for_status()
                st.session_state.filename = uploaded.name
                st.session_state.indexed = False
                st.success(f"Document envoyé : {uploaded.name}")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Erreur lors de l'envoi : {exc}")

    st.header("2. Indexation")

    if st.session_state.filename:
        st.info(f"Fichier actuel : {st.session_state.filename}")

    if st.button("Lancer l'indexation", disabled=st.session_state.filename is None):
        progress = st.progress(0, text="Démarrage de l'indexation...")
        try:
            progress.progress(20, text="Lecture du document...")
            resp = requests.post(
                f"{BACKEND_URL}/index",
                json={"filename": st.session_state.filename},
                timeout=120
            )
            progress.progress(60, text="Création des embeddings...")
            resp.raise_for_status()
            progress.progress(100, text="Indexation terminée !")
            st.session_state.indexed = True
            st.success("✅ Indexation terminée !")
            st.rerun()
        except requests.RequestException as exc:
            progress.empty()
            st.error(f"Erreur lors de l'indexation : {exc}")

    if st.session_state.indexed:
        st.success("✅ Document indexé — vous pouvez poser des questions")

    st.divider()
    st.header("📋 Historique")
    if st.session_state.historique:
        if st.button("🗑️ Effacer l'historique"):
            st.session_state.historique = []
            st.rerun()
        for i, item in enumerate(reversed(st.session_state.historique)):
            with st.expander(f"Q{len(st.session_state.historique) - i} : {item['question'][:40]}..."):
                st.write(item['answer'])
    else:
        st.caption("Aucune question posée pour l'instant.")

# --- Zone principale ---
st.header("3. Poser une question")

# Le warning ne s'affiche que si nécessaire
if not st.session_state.indexed:
    if not st.session_state.filename:
        st.warning("⚠️ Veuillez d'abord sélectionner ou charger un document.")
    else:
        st.warning("⚠️ Veuillez lancer l'indexation avant de poser une question.")

question = st.text_input(
    "Votre question",
    placeholder="Que dit le texte sur l'éducation ?",
    disabled=not st.session_state.indexed
)

if st.button("Interroger", type="primary", disabled=not question or not st.session_state.indexed):
    with st.spinner("Recherche et génération de la réponse..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/ask",
                json={"question": question},
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()

            st.subheader("Réponse")
            st.write(data.get("answer", ""))

            sources = data.get("sources", [])
            st.info(f"🔍 {len(sources)} passage(s) trouvé(s) dans le document")

            st.subheader("Sources")
            if sources:
                for s in sources:
                    with st.expander(
                        f"📄 {s['filename']} — passage {s['passage_id']}"
                        + (f" (score {s['score']:.3f})" if s.get("score") is not None else "")
                    ):
                        st.write(s["excerpt"])
            else:
                st.info("Aucune source trouvée.")

            st.session_state.historique.append({
                "question": question,
                "answer": data.get("answer", "")
            })

        except requests.RequestException as exc:
            st.error(f"Erreur lors de l'appel au backend : {exc}")