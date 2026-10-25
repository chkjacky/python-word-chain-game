from pydantic import BaseModel

from app.models.enums import Difficulty

LENGTH_BANDS = {
    Difficulty.EASY: (4, 6),
    Difficulty.MEDIUM: (6, 8),
    Difficulty.HARD: (8, 12),
}


class ValidationResult(BaseModel):
    valid: bool
    reason: str | None = None


def validate_chain_link(
    word: str, last_letter: str, used_words: list[str], difficulty: Difficulty
) -> ValidationResult:
    normalized = word.strip().lower()
    normalized_used = {w.strip().lower() for w in used_words}
    min_len, max_len = LENGTH_BANDS[difficulty]

    if not normalized.startswith(last_letter.strip().lower()):
        return ValidationResult(valid=False, reason="wrong_letter")
    if normalized in normalized_used:
        return ValidationResult(valid=False, reason="repeated_word")
    if not (min_len <= len(normalized) <= max_len):
        return ValidationResult(valid=False, reason="invalid_length")

    return ValidationResult(valid=True)
