# Stage 12 — Domain-generalized recovery experiment

{
  "stage": 12,
  "title": "Domain-generalized, variable-resolution recovery experiment",
  "files_created": [
    "ourionspectra/generalized_recovery.py",
    "ourionspectra/train_generalized_recovery.py",
    "ourionspectra/evaluate_stage12.py",
    "tests/test_stage12_generalization.py",
    "artifacts/recovery_model/stage12/model.pt",
    "artifacts/recovery_model/stage12/training_report.json",
    "artifacts/recovery_model/stage12/wasp_test_evaluation.json",
    "artifacts/recovery_model/stage12/external_evaluation.json",
    "artifacts/recovery_model/stage12/training_curve.png",
    "artifacts/recovery_model/stage12/external_rmse_comparison.png"
  ],
  "training": {
    "samples": 800,
    "validation": 150,
    "epochs": 8,
    "seed": 4212,
    "external_targets_used": false,
    "test_used": false
  },
  "design": [
    "variable-length input",
    "explicit wavelength and local spacing",
    "observed-mask channel",
    "wavelength-aware local baseline",
    "stratified channel-retention augmentation",
    "no interpolation or invented wavelength regions"
  ],
  "results": {
    "wasp39b_test": {
      "test_samples": 150,
      "rmse": 0.010142261217593936,
      "mae": 0.006775588640045247,
      "raw_rmse": 0.019163423526943453,
      "raw_mae": 0.010612845454138601,
      "test_used_for_training": false
    },
    "hatp1b_external": {
      "stage": 12,
      "target": "HAT-P-1b",
      "external_evaluation_only": true,
      "results": [
        {
          "scale": 0.5,
          "raw_rmse": 8.145490216676098e-05,
          "baseline_rmse": 0.00017849336068683503,
          "neural_rmse": 0.00020627556223633918,
          "raw_mae": 6.606740574467339e-05,
          "baseline_mae": 0.0001354438084957273,
          "neural_mae": 0.00016392549203068376
        },
        {
          "scale": 1.0,
          "raw_rmse": 0.00016153433171303786,
          "baseline_rmse": 0.0001844858116376006,
          "neural_rmse": 0.00023612099152981657,
          "raw_mae": 0.00012958258010621653,
          "baseline_mae": 0.0001432528182523148,
          "neural_mae": 0.0001938387572426633
        },
        {
          "scale": 1.5,
          "raw_rmse": 0.0002371490381128285,
          "baseline_rmse": 0.0001966490853253645,
          "neural_rmse": 0.0002814045631803547,
          "raw_mae": 0.00018891902398538398,
          "baseline_mae": 0.00015446127654571127,
          "neural_mae": 0.0002339148644344136
        },
        {
          "scale": 2.0,
          "raw_rmse": 0.0003192909711098393,
          "baseline_rmse": 0.00020835070557639022,
          "neural_rmse": 0.0003283983461470686,
          "raw_mae": 0.00025401756403241934,
          "baseline_mae": 0.00016610217972557777,
          "neural_mae": 0.00027535637971359134
        }
      ],
      "limitations": [
        "No external target used for training or model selection.",
        "The independent spectrum has a much coarser grid and different uncertainty scale than WASP-39b.",
        "This is a synthetic-noise stress test of a published reference candidate, not raw time-series recovery."
      ]
    }
  },
  "limitations": [
    "Clean target diversity remains one WASP-39b reference candidate; this stage improves observation/grid robustness, not true planetary-shape diversity.",
    "HAT-P-1b remains evaluation-only and is not used for model selection.",
    "The Stage 12 model does not yet outperform raw observations on the independent HAT-P-1b stress test, so it must not be integrated into the application as a claimed general solution.",
    "External spectrum is a published binned reference candidate, not ground truth and not raw time-series recovery."
  ]
}