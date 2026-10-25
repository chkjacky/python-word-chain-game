from wordfreq import zipf_frequency

from app.models.enums import Difficulty

ZIPF_THRESHOLDS = {
    Difficulty.EASY: 4.0,
    Difficulty.MEDIUM: 2.5,
    Difficulty.HARD: 2.5,
}


def classify_frequency(word: str) -> float:
    return zipf_frequency(word.strip().lower(), "en")


def is_difficulty_compliant(word: str, difficulty: Difficulty) -> bool:
    zipf = classify_frequency(word)
    threshold = ZIPF_THRESHOLDS[difficulty]
    if difficulty == Difficulty.HARD:
        return zipf < threshold
    return zipf >= threshold
