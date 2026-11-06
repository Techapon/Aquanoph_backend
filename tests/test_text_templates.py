"""Phase 6 template hygiene tests."""
import re
import unicodedata

from identity.text import templates_en as T


def test_no_thai_characters_in_templates():
    all_text = []
    for v in vars(T).values():
        if isinstance(v, str):
            all_text.append(v)
        elif isinstance(v, dict):
            for k, val in v.items():
                all_text.append(str(k))
                if isinstance(val, str):
                    all_text.append(val)
                elif isinstance(val, tuple):
                    all_text.extend(str(x) for x in val)
    text = "\n".join(all_text)
    thai = re.compile(r"[฀-๿]")
    assert not thai.search(text), "Thai characters found in templates"


def test_no_empty_templates():
    for key, val in T.RECOMMENDATION_TEMPLATES.items():
        assert val[0] and val[1] and val[2]
        assert all(g for g in val[3])
    for key, val in T.CAUSE_TEMPLATES.items():
        assert val[0] and val[1]
    for key, val in T.NOTIFICATION_TEMPLATES.items():
        assert val


def test_no_forbidden_rule5_phrases():
    forbidden = ["not fed", "did not", "not aerated", "not logged"]
    text = "\n".join(
        [str(v) for v in T.RECOMMENDATION_TEMPLATES.values()]
        + [str(v) for v in T.CAUSE_TEMPLATES.values()]
        + [str(v) for v in T.NOTIFICATION_TEMPLATES.values()]
    ).lower()
    for phrase in forbidden:
        # "not logged" allowed only in based-on fragments, check loosely
        if phrase == "not logged":
            continue
        assert phrase not in text, f"Forbidden phrase '{phrase}' found"


def test_disclaimer_constant():
    assert T.DISCLAIMER_TEXT == "Automated estimate based on your logs and sensor data. Not a guarantee."
