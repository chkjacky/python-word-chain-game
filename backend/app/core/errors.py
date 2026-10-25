from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    code: str = "app_error"
    status_code: int = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidWordError(AppError):
    code = "invalid_word"
    status_code = 422


class GameNotFoundError(AppError):
    code = "game_not_found"
    status_code = 404


class ToolUnavailableError(AppError):
    code = "tool_unavailable"
    status_code = 503


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
