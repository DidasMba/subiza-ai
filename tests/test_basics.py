"""Checks that run without a Gemini API key."""

from pathlib import Path

from app.handoff import needs_human
from app.prompts import build_prompt
from app.rag import load_chunks


def test_chunks_split_on_h3_headings():
    chunks = load_chunks(Path("app/knowledge/business_faq.md"))
    titles = [c["title"] for c in chunks]
    assert "Business Hours" in titles
    assert "Payment Methods" in titles
    # The "# Pharmacy Knowledge Base" title and the example-data note are dropped.
    assert all(c["text"].startswith("### ") for c in chunks)


def test_handoff_detection():
    assert needs_human("Please speak with the on-duty pharmacist.")
    assert needs_human("I'm not sure — a team member will follow up.")
    assert not needs_human("We are open 7:30 AM to 9:30 PM.")


def test_prompt_keeps_safety_rule_and_context():
    prompt = build_prompt("When do you open?", [{"title": "Hours", "text": "7:30 AM"}])
    assert "NEVER give medical advice" in prompt
    assert "[Hours]\n7:30 AM" in prompt
    assert prompt.endswith("Customer question: When do you open?")


def test_prompt_asks_for_the_question_language_next_to_the_question():
    prompt = build_prompt("Do you deliver?", [{"title": "Livraison", "text": "Nous livrons."}])
    before, question = prompt.rsplit("\n\n", 1)
    assert question == "Customer question: Do you deliver?"
    assert before.endswith("Reply in the language of the customer question below.")
