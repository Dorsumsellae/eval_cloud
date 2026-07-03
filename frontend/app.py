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

# --- Barre laterale : chargement et indexation ---
with st.sidebar:
    st.header("1. Document")
    uploaded = st.file_uploader("Charger un document (.txt)", type=["txt", "pdf"])

    if st.button("Envoyer le document", disabled=uploaded is None):
        # TODO (etudiant) : POST /upload avec le fichier
        st.info("A implementer : appel POST /upload")

    st.header("2. Indexation")
    if st.button("Lancer l'indexation"):
        # TODO (etudiant) : POST /index avec le nom du fichier
        st.info("A implementer : appel POST /index")

# --- Zone principale : question / reponse ---
st.header("3. Poser une question")
question = st.text_input("Votre question", placeholder="Que dit le texte sur l'éducation ?")

if st.button("Interroger", type="primary", disabled=not question):
    # TODO (etudiant) : POST /ask puis afficher reponse + sources
    try:
        resp = requests.post(
            f"{BACKEND_URL}/ask", json={"question": question}, timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        st.subheader("Réponse")
        st.write(data.get("answer", ""))

        st.subheader("Sources")
        for s in data.get("sources", []):
            with st.expander(
                f"{s['filename']} — passage {s['passage_id']}"
                + (f" (score {s['score']:.3f})" if s.get("score") is not None else "")
            ):
                st.write(s["excerpt"])
    except requests.RequestException as exc:
        st.error(f"Erreur lors de l'appel au backend : {exc}")
