from unittest.mock import AsyncMock, Mock

from app.agents import orchestrator
from app.domain.chain_rules import ValidationResult
from app.models.chain_session import ChainSession
from app.models.enums import Difficulty, GameStatus


def _sample_chain_session():
    return ChainSession(
        game_id="gm_1",
        username="jacky",
        difficulty=Difficulty.MEDIUM,
        current_round=1,
        total_score=0,
        used_words=["dragon"],
        last_letter="n",
        game_status=GameStatus.IN_PROGRESS,
    )


async def test_run_turn_short_circuits_on_invalid_word(monkeypatch):
    monkeypatch.setattr(
        orchestrator.validator_agent,
        "run",
        Mock(return_value=ValidationResult(valid=False, reason="wrong_letter")),
    )
    judge_mock = AsyncMock()
    generate_mock = AsyncMock()
    monkeypatch.setattr(orchestrator.creativity_judge_agent, "judge", judge_mock)
    monkeypatch.setattr(
        orchestrator.move_generator_agent, "generate_move", generate_mock
    )

    result = await orchestrator.run_turn(_sample_chain_session(), "radio")

    assert result.valid is False
    assert result.reason == "wrong_letter"
    judge_mock.assert_not_called()
    generate_mock.assert_not_called()


async def test_run_turn_calls_downstream_agents_with_projected_last_letter(monkeypatch):
    from app.agents.creativity_agent import CreativityJudgement

    monkeypatch.setattr(
        orchestrator.validator_agent,
        "run",
        Mock(return_value=ValidationResult(valid=True)),
    )
    judge_mock = AsyncMock(
        return_value=CreativityJudgement(creative=True, reason="clever")
    )
    generate_mock = AsyncMock(return_value="radio")
    monkeypatch.setattr(orchestrator.creativity_judge_agent, "judge", judge_mock)
    monkeypatch.setattr(
        orchestrator.move_generator_agent, "generate_move", generate_mock
    )

    chain_session = _sample_chain_session()
    result = await orchestrator.run_turn(chain_session, "nectar")

    assert result.valid is True
    assert result.creative is True
    assert result.ai_word == "radio"

    judge_mock.assert_awaited_once_with(chain_session, "nectar")

    generate_mock.assert_awaited_once()
    projected_session = generate_mock.await_args.args[0]
    assert projected_session.last_letter == "r"
    assert "nectar" in projected_session.used_words
    assert chain_session.last_letter == "n"
    assert "nectar" not in chain_session.used_words
