# Stage 15 — Final scientific validation

{
  "stage": 15,
  "summary": {
    "wasp39b": {
      "raw_rmse": 0.012895914201792359,
      "baseline_rmse": 0.007009398492217318,
      "neural_rmse": 0.007989311113324085,
      "raw_mae": 0.009224580090757002,
      "baseline_mae": 0.00527591718941173,
      "neural_mae": 0.0060278924469615,
      "coverage_1sigma": 0.7723782559456398
    },
    "hatp26b": {
      "raw_rmse": 0.00013598236383739883,
      "baseline_rmse": 0.00011385834009518536,
      "neural_rmse": 0.0005013250836088039,
      "raw_mae": 9.986906425474157e-05,
      "baseline_mae": 8.52140564620767e-05,
      "neural_mae": 0.0004820515998389398,
      "coverage_1sigma": 0.05530864197530864
    },
    "wasp17b": {
      "raw_rmse": 0.0006101072741562047,
      "baseline_rmse": 0.0003609913568045422,
      "neural_rmse": 0.0004062522624290789,
      "raw_mae": 0.0003276989882812544,
      "baseline_mae": 0.0002216669213055464,
      "neural_mae": 0.0002792543281194338,
      "coverage_1sigma": 0.6523039215686274
    },
    "hatp1b_external": {
      "raw_rmse": 0.0002417505922344027,
      "baseline_rmse": 0.0001734941681912625,
      "neural_rmse": 0.00024065436332441244,
      "raw_mae": 0.00019348941803035738,
      "baseline_mae": 0.00014084160488112495,
      "neural_mae": 0.00019704555079742822,
      "coverage_1sigma": 0.6486904761904762
    }
  },
  "external_holdout": "HAT-P-1b",
  "selection_decision": "NOT_READY_FOR_DEFAULT_INTEGRATION",
  "reason": "The multi-target neural model does not consistently outperform the transparent classical baseline across training-domain targets or the independent HAT-P-1b target.",
  "scientific_claim_allowed": "The model is an experimental multi-target recovery candidate; cross-target generalization is not yet established.",
  "plots": [
    "multitarget_rmse_benchmark.png",
    "uncertainty_coverage.png"
  ]
}