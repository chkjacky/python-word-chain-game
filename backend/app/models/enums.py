from enum import Enum


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GameStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    ENDED = "ended"
    QUIT = "quit"
