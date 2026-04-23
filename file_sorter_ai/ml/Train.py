from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from ml.Model import train_logreg


def main() -> int:
    # Placeholder training script — will be wired to DB label data later.
    x = np.zeros((4, 4), dtype=float)
    y = ["KEEP", "ARCHIVE", "NOT_NEEDED", "UNSURE"]
    model = train_logreg(x, y)
    Path("model.pkl").write_bytes(pickle.dumps(model))
    print("Wrote model.pkl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
