# Stage 10 — Independent external-spectrum validation

OurionSpectra now has an ingestion adapter for independently sourced published transmission spectra.

## Recommended source

The Stellar Planet archive curated by Dr Hannah Wakeford provides published transmission spectra in a common four-column format:

1. wavelength (µm)
2. wavelength uncertainty (µm)
3. `(Rp/R*)^2`
4. uncertainty in `(Rp/R*)^2`

Source: https://stellarplanet.org/science/exoplanet-transmission-spectra/

The NASA Exoplanet Archive Atmospheric Spectroscopy Table is the preferred authoritative cross-check for provenance and availability of peer-reviewed spectra. Its current documentation states that spectra are grouped into individual spectrum files and that the table provides wavelength, spectrum type, instrument/facility and file metadata.

Source: https://exoplanetarchive.ipac.caltech.edu/docs/atmospheres/atmospheres_home.html

## Important scientific rule

Do **not** copy an external spectrum into `data/wasp39b/training/`. External spectra are evaluation-only.

Do not call the external spectrum ground truth. Do not claim molecular detections from the recovery output alone.

The adapter performs only column conversion and wavelength sorting. It does not interpolate, smooth, offset-correct, or fabricate missing wavelengths.

## Why this stage is not yet a result

The project does not bundle a third-party spectrum because the exact source file, publication version, and reduction must be independently verified before a numerical cross-target result is reported. This keeps the final evaluation reproducible and auditable.
