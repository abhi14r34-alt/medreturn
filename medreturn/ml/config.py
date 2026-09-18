"""Training configuration.

CLASSES is the single source of truth for what the model can predict. It
is saved into the checkpoint, and the backend reads it back from there,
so the API can never claim a category the weights do not encode.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent

# Must match the folder names under ml/dataset/.
CLASSES: List[str] = [
    "Sharps",
    "Infectious",
    "Pharmaceutical",
    "Glass",
    "Plastic Recyclable",
    "General",
]


@dataclass
class TrainConfig:
    dataset_dir: Path = ROOT / "dataset"
    output_dir: Path = ROOT / "models"
    checkpoint_name: str = "model.pth"

    architecture: str = "mobilenet_v3_small"  # or "efficientnet_b0"
    pretrained: bool = True                    # transfer learning, not from scratch
    freeze_backbone_epochs: int = 3            # warm up the head first

    image_size: int = 224
    batch_size: int = 32
    epochs: int = 25
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    patience: int = 6                          # early stopping

    val_split: float = 0.15
    test_split: float = 0.15
    seed: int = 42
    num_workers: int = 2

    classes: List[str] = field(default_factory=lambda: list(CLASSES))

    @property
    def checkpoint_path(self) -> Path:
        return self.output_dir / self.checkpoint_name

    @property
    def metrics_path(self) -> Path:
        return self.output_dir / "metrics.json"


config = TrainConfig()
