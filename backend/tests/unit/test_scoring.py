from app.domain.scoring import score_turn


def test_cascade_triggers_at_streak_3():
    total, breakdown = score_turn("extraordinary", True, 3)

    assert total == 38
    assert breakdown.base == 10
    assert breakdown.creative == 5
    assert breakdown.cascade is True
    assert breakdown.length_bonus == 8


def test_no_cascade_at_streak_2():
    total, breakdown = score_turn("extraordinary", True, 2)

    assert total == 23
    assert breakdown.cascade is False
    assert breakdown.length_bonus == 8


def test_cascade_fires_again_at_streak_6():
    total, breakdown = score_turn("extraordinary", True, 6)

    assert breakdown.cascade is True
    assert total == 38


def test_exactly_five_letters_no_length_bonus():
    total, breakdown = score_turn("abcde", False, 0)

    assert total == 10
    assert breakdown.creative == 0
    assert breakdown.cascade is False
    assert breakdown.length_bonus == 0


def test_non_creative_word_never_cascades_even_at_streak_multiple_of_3():
    total, breakdown = score_turn("extraordinary", False, 3)

    assert breakdown.cascade is False
    assert breakdown.creative == 0
    assert total == 10 + 8
