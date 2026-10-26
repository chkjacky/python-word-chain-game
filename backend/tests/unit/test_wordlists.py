import pytest

from app.domain.chain_rules import LENGTH_BANDS
from app.domain.wordlists.loader import load_wordlist
from app.models.enums import Difficulty


@pytest.mark.parametrize(
    "difficulty", [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
)
def test_load_wordlist_returns_non_empty_list(difficulty):
    words = load_wordlist(difficulty)
    assert len(words) > 0


@pytest.mark.parametrize(
    "difficulty", [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
)
def test_load_wordlist_words_fit_length_band(difficulty):
    min_len, max_len = LENGTH_BANDS[difficulty]
    for word in load_wordlist(difficulty):
        assert min_len <= len(word) <= max_len


def test_hard_wordlist_never_ends_in_s():
    for word in load_wordlist(Difficulty.HARD):
        assert not word.lower().endswith("s")
