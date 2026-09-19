# Dataset format

Training expects one folder per class, named exactly as in `CLASSES` in
`ml/config.py`. `torchvision.datasets.ImageFolder` reads the labels from these
folder names, and `train.py` refuses to run if the folders and the config
disagree — a silent mismatch here would mislabel every prediction the API
makes.

```
ml/dataset/
├── Sharps/
│   ├── 0001.jpg
│   └── 0002.jpg
├── Infectious/
├── Pharmaceutical/
├── Glass/
├── Plastic Recyclable/
└── General/
```

## Requirements

- JPG, PNG or WebP. Minimum 64 px on the short side.
- Aim for at least 300–500 images per class before the numbers mean anything.
  Fewer than ~100 per class will overfit and the test split becomes too small
  to report honestly.
- Keep the classes roughly balanced, or the majority class dominates accuracy
  while the minority classes quietly fail.
- Photograph under the lighting and camera angle the real inlet will use.
  A model trained on clean product shots degrades badly on a conveyor.

## Before training

```bash
python -m ml.preprocessing.clean            # dry run: reports problems
python -m ml.preprocessing.clean --apply    # deletes unreadable, tiny, duplicate files
```

## Splits

`train.py` splits 70/15/15 (train/val/test) with a fixed seed. Validation drives
checkpoint selection and early stopping; the test split is touched only once, at
the end, and by `ml/evaluate.py`. Do not tune anything against the test split —
the reported figures stop being meaningful the moment you do.

## No dataset yet?

That is the expected state for a first prototype. The backend runs with
`DEMO_MODE=true`, returns clearly-labelled simulated results, and forces every
low-confidence item through human review. Nothing in the UI presents those
results as real inference. Collect and label a dataset, train, and the same code
path switches to real predictions with no changes to the API or frontend.
