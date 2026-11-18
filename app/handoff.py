"""Deciding when a conversation should go to a human."""

from pydantic import ValidationError

from app.schemas import AgentReply

# Fallback only, for replies that are not the structured JSON (see parse_reply).
# English-only: the structured `handoff` flag is what works in every language.
# Keep these in sync with the wording in prompts.py.
HANDOFF_PHRASES = [
    "not sure", "don't know", "team will", "follow up",
    "pharmacist", "speak with", "speak to",
]


def needs_human(reply: str) -> bool:
    reply = reply.lower()
    return any(phrase in reply for phrase in HANDOFF_PHRASES)


def parse_reply(text: str) -> tuple[str, bool]:
    """Read Gemini's answer: (message for the customer, hand off to a human?).

    Gemini is asked for JSON matching AgentReply, so the model itself decides
    on the handoff, whatever the customer's language. Text that is not that
    JSON falls back to the English phrase check.
    """
    try:
        parsed = AgentReply.model_validate_json(text)
    except ValidationError:
        reply = text.strip()
        return reply, needs_human(reply)
    reply = parsed.reply.strip()
    if not reply:
        raise ValueError("Gemini returned an empty reply")
    return reply, parsed.handoff
