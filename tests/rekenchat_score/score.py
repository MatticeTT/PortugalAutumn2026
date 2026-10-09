# De tests van de rekenchat (tests.py, letterlijk) importeren "score": dat is de rekencode van de app.
from pipeline.rules.score import *  # noqa: F403
from pipeline.rules.score import CATEGORIES, GO, breaking_height, score  # noqa: F401
