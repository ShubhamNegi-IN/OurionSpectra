# OURIONSPECTRA

Exoplanet Atmospheric Spectrum Recovery from Noisy Telescope Observations

OURIONSPECTRA is a machine-learning project developed for Smart India Hackathon 2026, based on Problem Statement SICT037: Exoplanet Atmospheric Spectrum Recovery from Noisy Telescope Observations.

Studying the atmosphere of a distant exoplanet often involves working with spectral data collected by telescopes. In practice, these observations are not perfectly clean. They can contain measurement noise, uncertainty, instrumental effects, and gaps in the observed wavelength range. These issues can make it difficult to distinguish actual spectral patterns from noise.

OURIONSPECTRA focuses on recovering a cleaner representation of an observed spectrum while retaining the information that may be useful for further scientific analysis.

The project provides an end-to-end workflow that covers spectral data preprocessing, realistic noisy-spectrum generation, machine learning based recovery, uncertainty estimation, atmospheric feature analysis, and model evaluation.

WASP-39b is used as the primary demonstration target. The system generates controlled noisy observations from available reference data and evaluates how effectively the recovery models can reconstruct the underlying spectral structure under different noise conditions.

The project is also designed to go beyond a single target. Additional datasets, including HAT-P-1b, HAT-P-26b, and WASP-17b, are used for external validation and cross-target evaluation. This helps us examine how the approach behaves when applied to spectra from different exoplanets.

Alongside the recovery models, the repository contains benchmarking tools, uncertainty and robustness analysis, diagnostic plots, scientific evaluation reports, trained model files, datasets, and automated tests.

The application also includes a FastAPI backend that provides an interface for processing and analysing spectral data.

Technology used:
Python, PyTorch, FastAPI, NumPy, Pandas, Matplotlib, and Pytest.

The goal of OURIONSPECTRA is to build a practical and transparent system that can help extract useful information from noisy exoplanet observations and provide a foundation for further atmospheric analysis.

Scientific note:
The reference spectrum used for WASP-39b is treated as a candidate/reference spectrum and not as absolute ground truth. The project acknowledges that observational astronomical data contains inherent uncertainties and limitations.
