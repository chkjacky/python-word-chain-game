from app.models.enums import Difficulty
from app.utils.frequency_lookup import classify_frequency, is_difficulty_compliant


def test_classify_frequency_common_word_is_high():
    assert classify_frequency("the") >= 6.0


def test_classify_frequency_uncommon_word_is_low():
    assert classify_frequency("quixotic") < 2.5


def test_is_difficulty_compliant_easy_common_word():
    assert is_difficulty_compliant("house", Difficulty.EASY) is True


def test_is_difficulty_compliant_hard_rejects_common_word():
    assert is_difficulty_compliant("house", Difficulty.HARD) is False


def test_is_difficulty_compliant_hard_accepts_uncommon_word():
    assert is_difficulty_compliant("quixotic", Difficulty.HARD) is True
