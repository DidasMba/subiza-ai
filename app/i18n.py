"""Fixed texts in the business's language: the chat widget and two agent replies.

Gemini already answers in the customer's language. These are the few texts that
never go through Gemini. Pick the language with UI_LANGUAGE ("en" or "fr").
"""

TEXTS = {
    "en": {
        "widget": {
            "greeting": (
                "Hi! 👋 I can help with opening hours, location, delivery, payments "
                "and our services. What would you like to know?"
            ),
            "status": "Online · AI assistant",
            "placeholder": "Ask about hours, delivery, payments…",
            "disclaimer": (
                "AI answers can be wrong. For health questions, please ask our pharmacist."
            ),
            "sources_label": "Based on",
            "handoff_notice": (
                "A member of our team will follow up. For anything urgent, "
                "please call the pharmacy."
            ),
            "typing": "Assistant is typing",
            "server_error": "Couldn't reach the server.",
            "retry": "Try again",
            "new_chat": "New conversation",
            "send": "Send message",
            "your_message": "Your message",
            "dark_mode": "Dark mode",
            "title_suffix": "Support",
        },
        "agent": {
            "no_match_reply": (
                "I'm not sure about that one — I've flagged it for our team "
                "and someone will get back to you shortly. In the meantime, "
                "is there anything else I can help with?"
            ),
            "busy_reply": (
                "Sorry, I'm having trouble answering right now. Please try again in a "
                "minute, or call the pharmacy and our team will help you directly."
            ),
        },
    },
    "fr": {
        "widget": {
            "greeting": (
                "Bonjour ! 👋 Je peux vous renseigner sur nos horaires, notre adresse, "
                "la livraison, les paiements et nos services. Que voulez-vous savoir ?"
            ),
            "status": "En ligne · Assistant IA",
            "placeholder": "Horaires, livraison, paiement…",
            "disclaimer": (
                "L'IA peut se tromper. Pour toute question de santé, demandez à notre pharmacien."
            ),
            "sources_label": "Sources :",
            "handoff_notice": (
                "Un membre de notre équipe va vous recontacter. En cas d'urgence, "
                "appelez la pharmacie."
            ),
            "typing": "L'assistant écrit",
            "server_error": "Impossible de joindre le serveur.",
            "retry": "Réessayer",
            "new_chat": "Nouvelle conversation",
            "send": "Envoyer le message",
            "your_message": "Votre message",
            "dark_mode": "Mode sombre",
            "title_suffix": "Assistance",
        },
        "agent": {
            "no_match_reply": (
                "Je ne suis pas sûr de pouvoir répondre à cette question. Je l'ai "
                "transmise à notre équipe, qui vous répondra rapidement. "
                "Puis-je vous aider pour autre chose ?"
            ),
            "busy_reply": (
                "Désolé, je n'arrive pas à répondre pour le moment. Réessayez dans une "
                "minute, ou appelez la pharmacie : notre équipe vous aidera directement."
            ),
        },
    },
}

DEFAULT_LANGUAGE = "en"


def language(requested: str) -> str:
    """The requested language if we have its texts, otherwise English."""
    requested = requested.strip().lower()
    return requested if requested in TEXTS else DEFAULT_LANGUAGE


def widget_texts(requested: str) -> dict[str, str]:
    return TEXTS[language(requested)]["widget"]


def agent_texts(requested: str) -> dict[str, str]:
    return TEXTS[language(requested)]["agent"]
