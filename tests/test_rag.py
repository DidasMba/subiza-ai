"""InMemoryStore retrieval, with a fake embedder instead of Gemini."""

from pathlib import Path

import pytest

from app.rag import InMemoryStore, load_chunks

# The bundled FAQs, whatever KB_PATH in .env points to.
KNOWLEDGE = Path(__file__).resolve().parent.parent / "app" / "knowledge"

CHUNKS = [
    {"title": "Hours", "text": "### Hours\nopen"},
    {"title": "Delivery", "text": "### Delivery\ndeliver"},
    {"title": "Payment", "text": "### Payment\npay"},
]
# Each keyword points along its own axis, so similarity is easy to predict.
AXES = {"open": [1, 0, 0], "deliver": [0, 1, 0], "pay": [0, 0, 1]}


def fake_embed(texts, task_type):
    return [next(v for k, v in AXES.items() if k in t) for t in texts]


def test_returns_best_match_above_min_score():
    store = InMemoryStore(CHUNKS, embed=fake_embed, min_score=0.3)
    matches = store.query("do you deliver?", top_k=3)
    assert [m["title"] for m in matches] == ["Delivery"]
    assert matches[0]["score"] == pytest.approx(1.0)


def test_empty_knowledge_base_is_rejected():
    with pytest.raises(ValueError):
        InMemoryStore([], embed=fake_embed)


@pytest.mark.parametrize("faq", sorted(KNOWLEDGE.glob("*.md")), ids=lambda path: path.name)
def test_every_faq_section_becomes_a_chunk(faq):
    chunks = load_chunks(faq)
    assert len(chunks) == faq.read_text(encoding="utf-8").count("\n### ")


def test_english_example_ends_with_human_help():
    chunks = load_chunks(KNOWLEDGE / "business_faq.md")
    assert chunks[-1]["title"] == "Contact for Pharmacist / Human Help"
