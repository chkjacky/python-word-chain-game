MODEL_RATES_USD_PER_1K_TOKENS = {
    "gpt-5-mini": {"input": 0.00015, "output": 0.0006},
}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = MODEL_RATES_USD_PER_1K_TOKENS.get(model)
    if rates is None:
        return 0.0
    return (tokens_in / 1000) * rates["input"] + (tokens_out / 1000) * rates["output"]
