from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass
class ClassificationModel:
    model: LogisticRegression
    labels: list[str]

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)

    def predict(self, x: np.ndarray) -> list[str]:
        idx = self.model.predict(x)
        return [self.labels[int(i)] for i in idx]


def train_logreg(x: np.ndarray, y: Iterable[str]) -> ClassificationModel:
    y_list = list(y)
    labels = sorted(set(y_list))
    label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
    y_idx = np.array([label_to_idx[v] for v in y_list], dtype=int)

    clf = LogisticRegression(max_iter=200)
    clf.fit(x, y_idx)
    return ClassificationModel(model=clf, labels=labels)

