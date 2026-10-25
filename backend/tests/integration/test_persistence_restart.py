from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from litellm.types.utils import Choices, Message, ModelResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.creativity_agent import creativity_judge_agent
from app.agents.move_generator_agent import move_generator_agent
from app.api.deps import get_db
from app.main import app
from app.models.orm import Base


def _fake_response(content: str) -> ModelResponse:
    return ModelResponse(
        id="chatcmpl-test",
        choices=[Choices(index=0, message=Message(role="assistant", content=content), finish_reason="stop")],
        model="gpt-5-mini",
    )


def _word_response(word: str) -> ModelResponse:
    return _fake_response(f'{{"word": "{word}"}}')


def _creativity_response(creative: bool, reason: str) -> ModelResponse:
    return _fake_response(f'{{"creative": {"true" if creative else "false"}, "reason": "{reason}"}}')


def _session_factory(engine):
    def get_db_override():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    return get_db_override


def test_game_state_survives_a_simulated_restart(tmp_path, monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)
    db_path = tmp_path / "durability_test.db"

    engine1 = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine1)
    app.dependency_overrides[get_db] = _session_factory(engine1)

    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(side_effect=[_word_response("dragon"), _word_response("rabbit")]),
    )
    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_creativity_response(True, "clever")),
    )

    with TestClient(app) as client1:
        start_response = client1.post(
            "/game/start", json={"username": "durability_user", "difficulty": "medium"}
        )
        game_id = start_response.json()["game_id"]
        client1.post(f"/game/{game_id}/turn", json={"word": "nectar"})
        client1.post(f"/game/{game_id}/quit")

        state_before = client1.get(f"/game/{game_id}/state").json()
        trace_before = client1.get(f"/game/{game_id}/trace").json()
        stats_before = client1.get("/stats/durability_user").json()

    app.dependency_overrides.clear()
    engine1.dispose()

    engine2 = create_engine(f"sqlite:///{db_path}")
    app.dependency_overrides[get_db] = _session_factory(engine2)

    with TestClient(app) as client2:
        state_after = client2.get(f"/game/{game_id}/state").json()
        trace_after = client2.get(f"/game/{game_id}/trace").json()
        stats_after = client2.get("/stats/durability_user").json()

    app.dependency_overrides.clear()
    engine2.dispose()

    assert state_after == state_before
    assert trace_after == trace_before
    assert stats_after == stats_before

    assert state_after["total_score"] > 0
    assert len(trace_after["trace"]) > 0
    assert stats_after["games_played"] == 1
