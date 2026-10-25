# Eval Report

## validation_accuracy
- passed: True
- cases: 22
- accuracy: 1.0

## creativity_calibration
- passed: False
- cases: 22
- precision: 1.0
- recall: 0.18181818181818182
- agreement: 0.5909090909090909

## hard_mode_no_s_compliance
- passed: True
- generations: 30
- s_ending_rate: 0.0
- average_retries: 0

## adversarial_robustness
- passed: True
- cases: 5

## performance
- note: Latency/cost observed during eval dimensions 2 & 3 only, not a full-game benchmark. See backend/scripts/measure_games.py (Step 12) for p50/p95 full-turn latency and cost-per-game-per-difficulty.
- p50_latency_ms: 3344.5
- p95_latency_ms: 5527.749999999998
- avg_cost_usd: 0.00016205480769230767
- samples: 52