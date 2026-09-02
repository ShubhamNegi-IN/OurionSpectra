"""
OurionSpectra — WASP-39b preprocessing

Purpose:
    Extract WASP-39b from the full spectral archive, generate a complete
    per-source quality report, and build a stitched high-resolution
    reference-spectrum candidate.

This script intentionally does NOT:
    - train an ML model
    - claim ground truth
    - detect molecules
    - fabricate missing spectral regions
"""

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

INPUT = Path("spectral_archive.csv")
OUTDIR = Path("wasp39b_preprocessed")
OUTDIR.mkdir(parents=True, exist_ok=True)

PRIMARY_FILES = [
    "WASP_39_b_3.11466_5078_1.tbl",
    "WASP_39_b_3.11466_5077_1.tbl",
]

VALIDATION_FILES = [
    "WASP_39_b_3.11466_5087_1.tbl",
    "WASP_39_b_3.11466_5502_6.tbl",
    "WASP_39_b_3.11466_4988_1.tbl",
    "WASP_39_b_3.11466_4988_2.tbl",
    "WASP_39_b_3.11466_4988_3.tbl",
    "WASP_39_b_3.11466_4988_4.tbl",
    "WASP_39_b_3.11466_5040_1.tbl",
]

GRID_STEP = 0.005
MAX_INTERP_GAP = 0.03

def main():
    df = pd.read_csv(INPUT)
    df["planet_clean"] = (
        df["planet"].astype(str)
        .str.strip()
        .str.strip("'")
        .str.strip('"')
    )
    wasp = df[df["planet_clean"].str.lower().eq("wasp-39 b")].copy()

    if wasp.empty:
        raise RuntimeError("No WASP-39 b rows found in the input archive.")

    # Per-source quality report
    quality_rows = []
    for fname, x in wasp.groupby("spectrum_file", sort=True):
        x = x.sort_values("wavelength_micron")
        wl = x["wavelength_micron"].to_numpy(float)
        flux = x["FLAM_W_m2_micron"].to_numpy(float)
        e1 = x["FLAMERR1"].to_numpy(float)
        e2 = x["FLAMERR2"].to_numpy(float)
        sigma = np.nanmax(np.vstack([np.abs(e1), np.abs(e2)]), axis=0)
        rel = sigma / np.maximum(np.abs(flux), 1e-300)
        diffs = np.diff(wl)

        if len(x) <= 2:
            classification = "photometric_or_very_sparse"
        elif x["bandwidth_micron"].median() == 0.25:
            classification = "low_resolution_long_wavelength"
        elif fname in PRIMARY_FILES:
            classification = "primary_reference_candidate"
        elif fname in VALIDATION_FILES:
            classification = "independent_validation_candidate"
        else:
            classification = "supporting_observation"

        quality_rows.append({
            "spectrum_file": fname,
            "n_points": len(x),
            "wavelength_min_micron": wl.min(),
            "wavelength_max_micron": wl.max(),
            "wavelength_span_micron": wl.max() - wl.min(),
            "median_bandwidth_micron": x["bandwidth_micron"].median(),
            "median_relative_flux_error": np.nanmedian(rel),
            "max_wavelength_gap_micron": diffs.max() if len(diffs) else np.nan,
            "classification": classification,
        })

    pd.DataFrame(quality_rows).to_csv(
        OUTDIR / "wasp39b_quality_report.csv", index=False
    )

    # Build common grid from the primary reference range.
    p = wasp[wasp.spectrum_file.isin(PRIMARY_FILES)]
    grid = np.arange(
        math.floor(p.wavelength_micron.min() / GRID_STEP) * GRID_STEP,
        math.ceil(p.wavelength_micron.max() / GRID_STEP) * GRID_STEP
        + GRID_STEP / 2,
        GRID_STEP,
    )

    source_data = {}
    for fname in PRIMARY_FILES:
        x = wasp[wasp.spectrum_file == fname].sort_values("wavelength_micron")
        wl = x["wavelength_micron"].to_numpy(float)
        flux = x["FLAM_W_m2_micron"].to_numpy(float)
        sigma = np.nanmax(
            np.vstack([
                np.abs(x["FLAMERR1"].to_numpy(float)),
                np.abs(x["FLAMERR2"].to_numpy(float)),
            ]),
            axis=0,
        )

        valid = np.isfinite(wl) & np.isfinite(flux) & np.isfinite(sigma) & (sigma > 0)
        wl, flux, sigma = wl[valid], flux[valid], sigma[valid]

        out_f = np.full(grid.shape, np.nan)
        out_s = np.full(grid.shape, np.nan)
        out_i = np.zeros(grid.shape, dtype=bool)

        for i, gx in enumerate(grid):
            if gx < wl[0] or gx > wl[-1]:
                continue

            j = np.searchsorted(wl, gx)

            if j < len(wl) and np.isclose(wl[j], gx, atol=1e-10):
                out_f[i], out_s[i] = flux[j], sigma[j]
                continue

            if j == 0 or j == len(wl):
                continue

            left, right = j - 1, j
            gap = wl[right] - wl[left]

            if gap > MAX_INTERP_GAP:
                continue

            t = (gx - wl[left]) / gap
            out_f[i] = flux[left] + t * (flux[right] - flux[left])
            out_s[i] = sigma[left] + t * (sigma[right] - sigma[left])
            out_i[i] = True

        source_data[fname] = (out_f, out_s, out_i)

    F = np.vstack([source_data[f][0] for f in PRIMARY_FILES])
    S = np.vstack([source_data[f][1] for f in PRIMARY_FILES])
    I = np.vstack([source_data[f][2] for f in PRIMARY_FILES])

    weights = np.where(
        np.isfinite(F) & np.isfinite(S) & (S > 0),
        1.0 / (S ** 2),
        0.0,
    )
    wsum = weights.sum(axis=0)

    ref_flux = np.full(grid.shape, np.nan)
    ref_sigma = np.full(grid.shape, np.nan)
    good = wsum > 0

    ref_flux[good] = (weights[:, good] * F[:, good]).sum(axis=0) / wsum[good]
    ref_sigma[good] = np.sqrt(1.0 / wsum[good])

    median_flux = np.nanmedian(ref_flux)

    reference = pd.DataFrame({
        "wavelength_micron": grid,
        "FLAM_reference_W_m2_micron": ref_flux,
        "FLAM_uncertainty_W_m2_micron": ref_sigma,
        "normalized_flux": ref_flux / median_flux,
        "normalized_uncertainty": ref_sigma / median_flux,
        "n_primary_sources": (weights > 0).sum(axis=0).astype(int),
        "interpolated_from_native_grid": np.any((weights > 0) & I, axis=0),
    })

    reference.to_csv(
        OUTDIR / "wasp39b_reference.csv",
        index=False,
        na_rep="",
    )

    metadata = {
        "target": "WASP-39 b",
        "input_file": str(INPUT),
        "wasp39b_rows": int(len(wasp)),
        "wasp39b_source_files": int(wasp.spectrum_file.nunique()),
        "primary_reference_files": PRIMARY_FILES,
        "validation_files": VALIDATION_FILES,
        "grid_step_micron": GRID_STEP,
        "max_interpolation_gap_micron": MAX_INTERP_GAP,
        "reference_type": "stitched high-resolution reference candidate",
        "not_ground_truth": True,
    }

    with open(OUTDIR / "wasp39b_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Created:", OUTDIR / "wasp39b_quality_report.csv")
    print("Created:", OUTDIR / "wasp39b_reference.csv")
    print("Created:", OUTDIR / "wasp39b_metadata.json")

if __name__ == "__main__":
    main()
