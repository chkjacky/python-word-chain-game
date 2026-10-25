import type {
  ApiError,
  GameStateResponse,
  LeaderboardEntry,
  QuitResponse,
  StartGameRequest,
  StartGameResponse,
  StatsResponse,
  TraceResponse,
  TurnRequest,
  TurnResponse,
} from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error implements ApiError {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.status = status;
  }
}

function normalizeErrorBody(status: number, body: unknown): ApiRequestError {
  if (body && typeof body === "object" && "error" in body) {
    const { code, message } =
      (body as { error: { code?: string; message?: string } }).error ?? {};
    return new ApiRequestError(
      code ?? "unknown_error",
      message ?? "Something went wrong",
      status,
    );
  }

  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (Array.isArray(detail)) {
      const message = detail
        .map((d) =>
          d && typeof d === "object" && "msg" in d
            ? String((d as { msg: unknown }).msg)
            : String(d),
        )
        .join("; ");
      return new ApiRequestError(
        "validation_error",
        message || "Invalid request",
        status,
      );
    }
    return new ApiRequestError("validation_error", String(detail), status);
  }

  return new ApiRequestError("unknown_error", "Something went wrong", status);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new ApiRequestError("network_error", "Could not reach the server", 0);
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // no JSON body
    }
    throw normalizeErrorBody(response.status, body);
  }

  return (await response.json()) as T;
}

export function startGame(data: StartGameRequest): Promise<StartGameResponse> {
  return request<StartGameResponse>("/game/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function playTurn(
  gameId: string,
  data: TurnRequest,
): Promise<TurnResponse> {
  return request<TurnResponse>(`/game/${gameId}/turn`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getState(gameId: string): Promise<GameStateResponse> {
  return request<GameStateResponse>(`/game/${gameId}/state`);
}

export function getTrace(gameId: string): Promise<TraceResponse> {
  return request<TraceResponse>(`/game/${gameId}/trace`);
}

export function quitGame(gameId: string): Promise<QuitResponse> {
  return request<QuitResponse>(`/game/${gameId}/quit`, { method: "POST" });
}

export function getStats(username: string): Promise<StatsResponse> {
  return request<StatsResponse>(`/stats/${encodeURIComponent(username)}`);
}

export function getLeaderboard(): Promise<LeaderboardEntry[]> {
  return request<LeaderboardEntry[]>("/leaderboard");
}
