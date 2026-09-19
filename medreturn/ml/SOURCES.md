# Public pilot dataset

`preprocessing/prepare_pilot_dataset.py` prepares a separate training dataset
from the public [Pharmaceutical and Biomedical Waste (PBW)](https://www.kaggle.com/datasets/engineeringubu/pharmaceutical-and-biomedical-waste)
archive. PBW is licensed **CC BY-NC-SA 4.0**; retain attribution and review the
licence before any commercial use.

PBW uses item-level labels while MedReturn has broad disposal routes. The
preparation utility records the exact source-to-route mapping in
`dataset_manifest.json`, skips source-generated augmented versions so they do
not leak into the held-out split, and copies existing local images without
modifying them.

This source is for prototype training, not clinically validated autonomous
routing. Keep `DEMO_MODE=true` and human verification enabled until a separate,
representative, independently labelled deployment dataset has been evaluated.

```powershell
..\backend\.venv\Scripts\python -m ml.preprocessing.prepare_pilot_dataset
$env:ML_DATASET_DIR = (Resolve-Path .\ml\dataset_pilot_pbw)
$env:ML_OUTPUT_DIR = (Resolve-Path .\ml\models) / "pilot_pbw"
..\backend\.venv\Scripts\python -m ml.preprocessing.clean --apply
..\backend\.venv\Scripts\python -m ml.train
..\backend\.venv\Scripts\python -m ml.evaluate
```
