"""Interface Streamlit de l'assistant documentaire RAG.

Consomme l'API FastAPI (backend) : /upload, /index, /ask.
L'URL du backend est lue depuis la variable d'environnement BACKEND_URL.
"""

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

# --- Barre laterale : chargement et indexation ---
with st.sidebar:
    st.header("1. Document")

    # Option 1 : utiliser le fichier par défaut
    if st.button("📂 Utiliser le corpus fourni"):
        st.session_state.filename = "corpus_de_travail.txt"
        st.success("Fichier sélectionné : corpus_de_travail.txt")

    st.divider()

    # Option 2 : uploader un fichier
    uploaded = st.file_uploader("Ou charger un document (.txt)", type=["txt", "pdf"])

    if st.button("Envoyer le document", disabled=uploaded is None):
        with st.spinner("Envoi du document..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), "text/plain")}
                resp = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
                resp.raise_for_status()
                st.session_state.filename = uploaded.name
                st.session_state.indexed = False
                st.success(f"Document envoyé : {uploaded.name}")
            except requests.RequestException as exc:
                st.error(f"Erreur lors de l'envoi : {exc}")

    st.header("2. Indexation")

    if st.session_state.filename:
        st.info(f"Fichier actuel : {st.session_state.filename}")

    if st.button("Lancer l'indexation", disabled=st.session_state.filename is None):
        with st.spinner("Indexation en cours... (peut prendre quelques secondes)"):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/index",
                    json={"filename": st.session_state.filename},
                    timeout=120
                )
                resp.raise_for_status()
                st.session_state.indexed = True
                st.success("Indexation terminée !")
            except requests.RequestException as exc:
                st.error(f"Erreur lors de l'indexation : {exc}")

    if st.session_state.indexed:
        st.success("✅ Document indexé — vous pouvez poser des questions")

# --- Zone principale : question / reponse ---
st.header("3. Poser une question")

if not st.session_state.indexed:
    st.warning("⚠️ Veuillez d'abord charger et indexer un document.")

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

            st.subheader("Sources")
            sources = data.get("sources", [])
            if sources:
                for s in sources:
                    with st.expander(
                        f"📄 {s['filename']} — passage {s['passage_id']}"
                        + (f" (score {s['score']:.3f})" if s.get("score") is not None else "")
                    ):
                        st.write(s["excerpt"])
            else:
                st.info("Aucune source trouvée.")

        except requests.RequestException as exc:
            st.error(f"Erreur lors de l'appel au backend : {exc}")