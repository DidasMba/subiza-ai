"""Fixed texts for the widget and the agent, per UI_LANGUAGE."""

from app import i18n


def test_french_texts_for_widget_and_agent():
    assert i18n.language(" FR ") == "fr"
    assert i18n.widget_texts("fr")["greeting"].startswith("Bonjour")
    assert "pharmacie" in i18n.agent_texts("fr")["busy_reply"]


def test_unknown_language_falls_back_to_english():
    assert i18n.language("ln") == "en"
    assert i18n.widget_texts("ln") == i18n.TEXTS["en"]["widget"]


def test_every_language_has_the_same_keys():
    english = i18n.TEXTS["en"]
    for texts in i18n.TEXTS.values():
        assert texts["widget"].keys() == english["widget"].keys()
        assert texts["agent"].keys() == english["agent"].keys()
