from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    GameNotFoundError,
    InvalidWordError,
    ToolUnavailableError,
    register_exception_handlers,
)


def test_invalid_word_error_fields():
    exc = InvalidWordError("bad word")
    assert exc.code == "invalid_word"
    assert exc.status_code == 422
    assert exc.message == "bad word"


def test_game_not_found_error_fields():
    exc = GameNotFoundError("no such game")
    assert exc.code == "game_not_found"
    assert exc.status_code == 404
    assert exc.message == "no such game"


def test_tool_unavailable_error_fields():
    exc = ToolUnavailableError("dictionary down")
    assert exc.code == "tool_unavailable"
    assert exc.status_code == 503
    assert exc.message == "dictionary down"


def _build_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-invalid-word")
    async def raise_invalid_word():
        raise InvalidWordError("bad word")

    @app.get("/raise-game-not-found")
    async def raise_game_not_found():
        raise GameNotFoundError("no such game")

    @app.get("/raise-tool-unavailable")
    async def raise_tool_unavailable():
        raise ToolUnavailableError("dictionary down")

    return app


client = TestClient(_build_test_app())


def test_invalid_word_error_response_shape():
    response = client.get("/raise-invalid-word")
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "invalid_word", "message": "bad word"}}


def test_game_not_found_error_response_shape():
    response = client.get("/raise-game-not-found")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "game_not_found", "message": "no such game"}
    }


def test_tool_unavailable_error_response_shape():
    response = client.get("/raise-tool-unavailable")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "tool_unavailable", "message": "dictionary down"}
    }
