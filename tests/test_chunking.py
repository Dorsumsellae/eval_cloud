from backend.rag.chunking import chunk_text


def test_chunk_text_basic():
    text = "Phrase un. " * 200  # texte assez long pour forcer plusieurs chunks
    chunks = chunk_text(text, chunk_size=800, chunk_overlap=120)

    assert len(chunks) > 1
    # les index doivent être continus et commencer à 0
    assert [c.index for c in chunks] == list(range(len(chunks)))
    # aucun chunk ne doit dépasser largement la taille cible
    assert all(len(c.text) <= 800 + 50 for c in chunks)


def test_chunk_text_empty_string():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_short_text_single_chunk():
    text = "Un texte très court."
    chunks = chunk_text(text, chunk_size=800, chunk_overlap=120)
    assert len(chunks) == 1
    assert chunks[0].text == text
