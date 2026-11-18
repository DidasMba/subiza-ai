"""Request and response shapes shared by the API and the agent."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app import config


class Turn(BaseModel):
    """One earlier message in the conversation."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4 * config.MAX_MESSAGE_CHARS)


Message = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=config.MAX_MESSAGE_CHARS),
]


class ChatRequest(BaseModel):
    message: Message
    # Earlier turns, oldest first. The server is stateless, so the client
    # sends them; only the last MAX_HISTORY_TURNS are used.
    history: list[Turn] = Field(default_factory=list, max_length=50)


class AgentReply(BaseModel):
    """What Gemini must return: the message, and whether a human takes over.

    Asking for this shape lets the model flag a handoff in any language,
    instead of the server matching English phrases in the reply.
    """

    reply: str = Field(description="The message for the customer, in their language.")
    handoff: bool = Field(
        description=(
            "true when the reply sends the customer to the pharmacist or says a "
            "team member will follow up; false when the context answered the question."
        )
    )


class ChatResponse(BaseModel):
    reply: str
    handed_off: bool
    sources: list[str]


class WidgetInfo(BaseModel):
    business_name: str
    suggestions: list[str]
    max_message_chars: int
    language: str
    texts: dict[str, str]
