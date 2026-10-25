import pytest

from app.domain.chain_rules import validate_chain_link
from app.models.enums import Difficulty


@pytest.mark.parametrize(
    "word,last_letter,used_words,difficulty,expected_valid,expected_reason",
    [
        ("nectar", "n", [], Difficulty.MEDIUM, True, None),
        ("radio", "x", [], Difficulty.MEDIUM, False, "wrong_letter"),
        ("nectar", "n", ["nectar"], Difficulty.MEDIUM, False, "repeated_word"),
        ("ox", "o", [], Difficulty.EASY, False, "invalid_length"),
        ("extraordinarily", "e", [], Difficulty.HARD, False, "invalid_length"),
        (" Nectar ", "N", ["nectar"], Difficulty.MEDIUM, False, "repeated_word"),
    ],
)
def test_validate_chain_link(word, last_letter, used_words, difficulty, expected_valid, expected_reason):
    result = validate_chain_link(word, last_letter, used_words, difficulty)

    assert result.valid is expected_valid
    assert result.reason == expected_reason
