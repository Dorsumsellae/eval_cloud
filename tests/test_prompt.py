from backend.rag.llm import build_context, build_prompt


def test_build_prompt_contains_question_and_context():
    prompt = build_prompt(context="Le ciel est bleu.", question="De quelle couleur est le ciel ?")

    assert "Le ciel est bleu." in prompt
    assert "De quelle couleur est le ciel ?" in prompt
    assert "Je ne trouve pas cette information" in prompt  # consigne de repli présente


def test_build_prompt_instructs_context_only_answer():
    prompt = build_prompt(context="contexte quelconque", question="question quelconque")
    assert "Réponds uniquement à partir du contexte" in prompt


def test_build_context_joins_multiple_docs():
    docs = [{"text": "Passage A"}, {"text": "Passage B"}]
    context = build_context(docs)
    assert "Passage A" in context
    assert "Passage B" in context


def test_build_context_empty_list():
    assert build_context([]) == ""
