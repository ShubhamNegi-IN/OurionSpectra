# OurionSpectra Stage 9 — Final Pre-Integration Scientific Validation

## Result
The current 4-input hybrid recovery model was evaluated on the untouched 150-sample synthetic test set. The test set was not used for training, model selection, or uncertainty calibration.

| Method | RMSE | MAE |
|---|---:|---:|
| Raw noisy spectrum | 0.0191634 | 0.0106128 |
| Moving average (11-point) | 0.0091728 | 0.0065531 |
| OurionSpectra neural recovery | **0.0078180** | **0.0051046** |

Relative RMSE improvement:
- vs raw noisy input: **59.2%**
- vs 11-point moving average: **14.8%**

Sample-level bootstrap difference (MA11 RMSE − neural RMSE):
- estimate: **0.0018697**
- 95% CI: **[0.0017012, 0.0020296]**

## Uncertainty
- 1-sigma coverage: **65.8%**
- 2-sigma coverage: **90.1%**

These are substantially closer to nominal Gaussian coverage than the earlier prototype, but are not evidence of observational calibration.

## Structure preservation
Average per-sample structure errors:

| Method | Gradient RMSE | Curvature RMSE |
|---|---:|---:|
| Raw noisy | 0.02061 | 0.03561 |
| Moving average | 0.00689 | 0.00955 |
| OurionSpectra neural | **0.00505** | **0.00749** |

The neural result therefore improves the benchmark metrics without simply increasing gradient/curvature error relative to the classical baseline.

## Readiness decision
**Pre-integration candidate: PASS for synthetic held-out benchmarking.**

However, this is **NOT a final scientific validation of cross-planet generalization**.

The remaining mandatory scientific limitation is that all synthetic clean targets originate from one WASP-39b reference candidate. The external-spectrum validation harness from Stage 8 is ready, but it has not yet been exercised with an independently sourced compatible reference spectrum.

Therefore:

- GUI: unchanged
- FastAPI recovery endpoint: unchanged
- Atmospheric feature detector: unchanged
- No molecular detections fabricated
- Reference spectrum is not called ground truth
- Test set remains isolated

## Reproducibility
Final benchmark seed: `9031`.

The final validation code is `ourionspectra/final_scientific_validation.py` and its tests are in `tests/test_final_scientific_validation.py`.

## Important implementation note
The Stage 8 package contained a stale checkpoint whose first convolution expected 3 input channels while the current Stage 7 source model expects 4 channels. Rather than silently mixing incompatible artifacts, Stage 9 created a consistent 4-channel checkpoint at:

`artifacts/recovery_model/stage9_model/model.pt`

The old checkpoint was not overwritten.
