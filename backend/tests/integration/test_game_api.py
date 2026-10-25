from unittest.mock import AsyncMock

import pytest
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


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_happy_path_start_turns_trace_quit(client, monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(side_effect=[_word_response("dragon"), _word_response("rabbit"), _word_response("yogurt")]),
    )
    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(
            side_effect=[
                _creativity_response(True, "clever pun"),
                _creativity_response(False, "obvious choice"),
            ]
        ),
    )

    start_response = client.post("/game/start", json={"username": "jacky", "difficulty": "medium"})
    assert start_response.status_code == 200
    start_body = start_response.json()
    assert start_body["ai_opening_word"] == "dragon"
    game_id = start_body["game_id"]

    turn1 = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})
    assert turn1.status_code == 200
    turn1_body = turn1.json()
    assert turn1_body["accepted"] is True
    assert turn1_body["ai_move"] == "rabbit"
    assert turn1_body["score_breakdown"]["creative"] == 5
    assert turn1_body["round"] == 1

    turn2 = client.post(f"/game/{game_id}/turn", json={"word": "turkey"})
    assert turn2.status_code == 200
    turn2_body = turn2.json()
    assert turn2_body["accepted"] is True
    assert turn2_body["ai_move"] == "yogurt"
    assert turn2_body["round"] == 2

    trace_response = client.get(f"/game/{game_id}/trace")
    assert trace_response.status_code == 200
    steps = [entry["step"] for entry in trace_response.json()["trace"]]
    assert "validate_word" in steps
    assert "judge_creativity" in steps
    assert "generate_ai_move" in steps

    quit_response = client.post(f"/game/{game_id}/quit")
    assert quit_response.status_code == 200
    assert quit_response.json()["game_status"] == "quit"

    quit_again = client.post(f"/game/{game_id}/quit")
    assert quit_again.status_code == 200
    assert quit_again.json()["final_score"] == quit_response.json()["final_score"]


def test_invalid_word_ends_the_game(client, monkeypatch):
    monkeypatch.setattr(move_generator_agent, "generate_move", AsyncMock(return_value="dragon"))

    start_response = client.post("/game/start", json={"username": "alice", "difficulty": "medium"})
    game_id = start_response.json()["game_id"]

    turn_response = client.post(f"/game/{game_id}/turn", json={"word": "zzz"})
    assert turn_response.status_code == 200
    body = turn_response.json()
    assert body["accepted"] is False
    assert body["reason"] == "wrong_letter"
    assert body["game_status"] == "ended"

    follow_up = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})
    assert follow_up.status_code == 200
    assert follow_up.json()["reason"] == "game_already_ended"
