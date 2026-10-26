from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    base: int
    creative: int
    cascade: bool
    length_bonus: int


def score_turn(
    word: str, is_creative: bool, cascade_streak: int
) -> tuple[int, ScoreBreakdown]:
    base = 10
    creative_bonus = 5 if is_creative else 0
    subtotal = base + creative_bonus

    cascade = is_creative and cascade_streak > 0 and cascade_streak % 3 == 0
    if cascade:
        subtotal *= 2

    length_bonus = max(0, len(word) - 5)
    total = subtotal + length_bonus

    return total, ScoreBreakdown(
        base=base,
        creative=creative_bonus,
        cascade=cascade,
        length_bonus=length_bonus,
    )
