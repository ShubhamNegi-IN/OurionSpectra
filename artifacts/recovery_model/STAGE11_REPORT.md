# OurionSpectra Stage 11 — Independent Target External Validation

## Purpose

Evaluate the frozen Stage 9 recovery model against an independently published exoplanet transmission-spectrum reference candidate that was never used for training, validation, calibration, or model selection.

## External target

HAT-P-1b, HST/WFC3 G141 transmission spectrum from Wakeford et al. (2013), MNRAS 435, 3481, Table 2. The published table contains 28 spectral bins from 1.1269 to 1.6453 micron with Rp/R* and 1-sigma uncertainty.

The evaluation converts:

- transit depth: D = (Rp/R*)^2
- uncertainty: sigma_D = 2 (Rp/R*) sigma_Rp/R*
- OurionSpectra flux-like representation: F/F* = 1 - D

No interpolation, smoothing, offset fitting, feature enhancement, or atmospheric-feature injection is performed.

## Evaluation design

The published spectrum is treated as a **reference observation/candidate, not ground truth**. Because the trained recovery model expects a noisy input plus an uncertainty field, controlled Gaussian perturbations are generated from the published uncertainty for four stress-test levels: 0.5x, 1.0x, 1.5x and 2.0x. Each level uses 100 independent realizations.

The external target remains evaluation-only.

## Result

The Stage 9 model does **not** generalize successfully to this external target under the current protocol. The neural recovery is worse than the moving-average baseline at all tested noise scales.

| Noise scale | Raw RMSE | Moving-average RMSE | Neural RMSE |
|---|---:|---:|---:|
| 0.5x | 0.0000802 | 0.0001611 | 0.0001917 |
| 1.0x | 0.0001581 | 0.0001660 | 0.0002431 |
| 1.5x | 0.0002453 | 0.0001793 | 0.0003265 |
| 2.0x | 0.0003210 | 0.0001881 | 0.0004155 |

The model's predicted 1-sigma intervals are very conservative on this target (approximately 100%, 100%, 100%, and 99.25% empirical coverage for the four noise scales), so uncertainty calibration is also not transferable yet.

## Scientific interpretation

This is a **useful negative result**. It shows that the current model's strong WASP-39b held-out benchmark cannot be treated as evidence of cross-planet generalization.

Likely contributors include:

1. training targets all originate from a single WASP-39b reference candidate;
2. HAT-P-1b has a much coarser 28-bin grid than the 909-point WASP-39b training grid;
3. the model uses a fixed WASP-39b wavelength-coordinate convention and index-space convolutional receptive fields;
4. the external spectrum comes from a different instrument/reduction and has different uncertainty characteristics;
5. no cross-target calibration or offset fitting was permitted, intentionally preserving the independence of the test.

## Decision

**Do not integrate the Stage 9 model into the GUI or FastAPI recovery endpoint yet.** The external validation has exposed a real generalization problem that should be addressed before user-facing deployment.
