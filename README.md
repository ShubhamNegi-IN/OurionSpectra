# OURIONSPECTRA

### Machine Learning for Exoplanet Atmospheric Spectrum Recovery

OURIONSPECTRA is a machine-learning-driven system developed for Smart India Hackathon 2026, Problem Statement SICT037: Exoplanet Atmospheric Spectrum Recovery from Noisy Telescope Observations.

The project focuses on recovering cleaner and more useful exoplanet spectra from noisy telescope observations. Astronomical spectra can contain measurement noise, uncertainty, instrumental effects, and missing wavelength regions, making it difficult to distinguish meaningful spectral structure from observational noise.

OURIONSPECTRA combines machine learning with scientific data processing and validation to address this problem.

## What the system does

The project provides an end-to-end workflow for:

* Generating realistic noisy spectral observations from reference data
* Training machine-learning models for spectrum recovery
* Recovering spectral signals from noisy observations
* Evaluating recovery performance using quantitative benchmarks
* Estimating and analysing prediction uncertainty
* Testing model robustness under different noise conditions
* Evaluating generalization across multiple exoplanet targets
* Performing external validation using independent spectral datasets
* Analysing spectral features for further atmospheric interpretation

## Machine Learning

Machine learning is at the core of OURIONSPECTRA.

The repository contains dedicated modules for spectrum recovery, generalized recovery, multitarget training, model evaluation, and uncertainty calibration. PyTorch-based models are trained using synthetic noisy observations generated from available spectral reference data.

The training pipeline supports different noise levels and signal-to-noise conditions, allowing the recovery models to be evaluated under controlled observational conditions.

The project also includes trained model artifacts and evaluation results so that the development and validation process can be examined alongside the source code.

## Data and Scientific Validation

WASP-39b is used as the primary demonstration target. Its reference spectral data is processed to create controlled noisy observations for training and evaluation.

The system also includes multi-target training and external validation data for:

* HAT-P-1b
* HAT-P-26b
* WASP-17b

This allows the project to evaluate whether the recovery approach can work beyond a single exoplanet.

The repository includes benchmark results, RMSE evaluations, robustness analysis, uncertainty-coverage analysis, diagnostic plots, and scientific validation reports.

## Project Architecture

```text
OURIONSPECTRA
│
├── ourionspectra/              # Core Python package
│   ├── api/                    # FastAPI routes and schemas
│   ├── model.py                # ML model components
│   ├── recovery_model.py       # Spectrum recovery
│   ├── generalized_recovery.py # Generalized recovery
│   ├── multitarget_data.py     # Multi-target data handling
│   ├── training_data.py        # Synthetic training data
│   ├── calibrate_uncertainty.py
│   ├── domain_robustness.py
│   ├── cross_target_evaluation.py
│   └── ...
│
├── data/                       # Spectral datasets
├── models/                     # Trained model files
├── artifacts/                  # Evaluation and validation results
├── tests/                      # Automated tests
├── assets/                     # Project graphics and icons
│
├── main.py                     # Application entry point
├── server.py                   # API/server entry point
├── requirements.txt            # Python dependencies
└── README.md
```

## Technology Stack

* Python
* PyTorch
* NumPy
* Pandas
* Matplotlib
* FastAPI
* Pytest

## Application

OURIONSPECTRA includes a FastAPI backend for handling spectrum-processing functionality and providing an interface between the application's components.

The repository also contains the supporting application files, trained models, datasets, scientific evaluation artifacts, and automated tests.

## Validation

The project follows a staged evaluation approach covering model performance, baseline comparison, robustness, uncertainty calibration, external validation, and multi-target evaluation.

This makes the repository more than a standalone ML model: it contains the surrounding data pipeline, evaluation framework, scientific analysis, and application layer required to test the recovery approach as a complete system.

## Scientific Note

The WASP-39b spectrum included in this project is treated as a candidate/reference spectrum and not as absolute ground truth. The system is designed with the understanding that observational astronomical data contains inherent measurement uncertainties and limitations.

## Project Goal

The goal of OURIONSPECTRA is to develop a practical machine-learning approach for recovering useful spectral information from noisy exoplanet observations and to evaluate its reliability across different observational conditions and exoplanet targets.
