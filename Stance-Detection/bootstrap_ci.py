"""
bootstrap_ci.py
===============

Bootstrap 95% confidence intervals for the precision, recall and F1 of each
class, computed from the test-set predictions saved by ``train_bertimbau.py``
(.npz file with ``predictions`` and ``labels``).

Classes: 0 = neutral, 1 = in favor, 2 = against (original label -1).

Usage:
    python bootstrap_ci.py
    python bootstrap_ci.py --predictions other_model.npz --output outputs/metrics/bootstrap_other.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

BOOTSTRAP_ITERATIONS = 5000
BOOTSTRAP_SEED = 2024
CLASSES = [0, 1, 2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap of the per-class metrics.")
    parser.add_argument("--predictions", default=str(OUTPUT_DIR / "predictions" / "test_predictions_and_labels.npz"),
                        help=".npz file with predictions and labels "
                             "(default: outputs/predictions/test_predictions_and_labels.npz).")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "metrics" / "bootstrap_results.csv"),
                        help="Output CSV (default: outputs/metrics/bootstrap_results.csv).")
    parser.add_argument("--iterations", type=int, default=BOOTSTRAP_ITERATIONS)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    return parser.parse_args()


def bootstrap_test(predictions, labels, n_iterations, seed):
    rng = np.random.default_rng(seed)
    idx = np.arange(labels.shape[0])
    scores = {f"{m}_class_{c}": [] for c in CLASSES for m in ("precision", "recall", "f1")}

    for i in range(n_iterations):
        if i % 100 == 0:
            print(f"Iteration {i}/{n_iterations}")
        boot = rng.choice(idx, size=idx.shape[0], replace=True)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels[boot], predictions[boot], labels=CLASSES, average=None, zero_division=0,
        )
        for c in CLASSES:
            scores[f"precision_class_{c}"].append(precision[c])
            scores[f"recall_class_{c}"].append(recall[c])
            scores[f"f1_class_{c}"].append(f1[c])

    return {
        name: {
            "mean": np.mean(values),
            "std": np.std(values),
            "lower_95_ci": np.percentile(values, 2.5),
            "upper_95_ci": np.percentile(values, 97.5),
        }
        for name, values in scores.items()
    }


def main() -> None:
    args = parse_args()
    data = np.load(args.predictions)
    ci_metrics = bootstrap_test(data["predictions"], data["labels"], args.iterations, args.seed)

    results = pd.DataFrame(ci_metrics).T
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output)
    print("Mean, standard deviation and confidence intervals of the per-class metrics:")
    print(results)


if __name__ == "__main__":
    main()
