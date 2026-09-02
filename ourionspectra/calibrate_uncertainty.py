"""Calibrate predictive uncertainty using validation data only.

A single multiplicative scale factor is fitted on validation residuals and then
frozen before the held-out test benchmark. This avoids using test labels for
uncertainty calibration.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, torch
from .recovery_model import SpectralRecoveryNet
from .train_recovery import SpectrumDataset, masked_moving_average


def fit(model_path, val_path, output):
    model=SpectralRecoveryNet(channels=32)
    ckpt=torch.load(model_path,map_location='cpu',weights_only=True); model.load_state_dict(ckpt['model_state']); model.eval()
    ds=SpectrumDataset(val_path); ratios=[]
    with torch.no_grad():
      for s in ds.samples:
        wl=np.asarray(s['wavelength'],np.float32); noisy=np.asarray(s['noisy_flux'],np.float32); sigma=np.asarray(s['noise_sigma'],np.float32); clean=np.asarray(s['clean_flux'],np.float32)
        valid=np.isfinite(clean)&np.isfinite(noisy)&np.isfinite(sigma)
        base=masked_moving_average(noisy,valid,5)
        x=np.stack([(wl-0.63)/(5.17-0.63),np.nan_to_num(noisy),np.nan_to_num(sigma),np.nan_to_num(base)],axis=0)
        mean,logsig=model(torch.from_numpy(x[None])); pred=mean[0,0].numpy(); ps=np.exp(logsig[0,0].numpy())
        z=np.abs(pred[valid]-clean[valid])/np.maximum(ps[valid],1e-6)
        ratios.append(z)
    z=np.concatenate(ratios)
    factor=float(np.quantile(z,0.68))
    # Conservative floor prevents pathological collapse while retaining the validation-derived scale.
    factor=max(factor,0.5)
    result={'stage':'7_uncertainty_calibration','method':'single validation-derived multiplicative scale','target_coverage':'68% within calibrated 1-sigma','calibration_factor':factor,'validation_samples':len(ds),'test_labels_used':False}
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8'); return result

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--val',default='data/wasp39b/training/val.json'); p.add_argument('--output',default='artifacts/recovery_model/stage7_uncertainty_calibration.json'); a=p.parse_args(); print(json.dumps(fit(a.model,a.val,a.output),indent=2))
