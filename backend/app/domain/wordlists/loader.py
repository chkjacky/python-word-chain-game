import json
from pathlib import Path

from app.models.enums import Difficulty

_WORDLIST_DIR = Path(__file__).parent
_FILENAMES = {
    Difficulty.EASY: "easy.json",
    Difficulty.MEDIUM: "medium.json",
    Difficulty.HARD: "hard.json",
}


def load_wordlist(difficulty: Difficulty) -> list[str]:
    path = _WORDLIST_DIR / _FILENAMES[difficulty]
    return json.loads(path.read_text())
