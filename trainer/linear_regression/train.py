import json
import os
import sys
import time
from typing import Dict

import joblib
import pandas as pd
import requests
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    v = os.environ.get(name, default)
    if required and not v:
        print(f"[trainer] Missing required env: {name}", file=sys.stderr)
        sys.exit(2)
    return v


def download(url: str, dest_path: str):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def upload_put(url: str, path: str, content_type: str = "application/octet-stream"):
    with open(path, "rb") as f:
        r = requests.put(url, data=f, headers={"Content-Type": content_type}, timeout=60)
        r.raise_for_status()


def main():
    t0 = time.time()
    # Accept either URL-based flow (recommended) or local PV paths.
    dataset_url = env("DATASET_URL")
    dataset_path = env("DATASET_PATH")  # used if DATASET_URL is not given

    x_col = env("X_COLUMN", required=True)
    y_col = env("Y_COLUMN", required=True)
    fit_intercept = env("FIT_INTERCEPT", "true").lower() == "true"

    output_dir = env("OUTPUT_DIR")  # PV path (if using volumes)
    out_model_url = env("OUTPUT_MODEL_URL")      # presigned PUT
    out_metrics_url = env("OUTPUT_METRICS_URL")  # presigned PUT

    tmp = "/tmp"
    os.makedirs(tmp, exist_ok=True)
    local_csv = os.path.join(tmp, "data.csv")
    local_model = os.path.join(tmp, "model.pkl")
    local_metrics = os.path.join(tmp, "metrics.json")

    # Fetch dataset
    if dataset_url:
        print(f"[trainer] downloading dataset from URL")
        download(dataset_url, local_csv)
    elif dataset_path:
        print(f"[trainer] reading local dataset from {dataset_path}")
        local_csv = dataset_path
    else:
        print("[trainer] No dataset source provided", file=sys.stderr)
        sys.exit(2)

    # Load data
    df = pd.read_csv(local_csv)
    if x_col not in df.columns or y_col not in df.columns:
        print(f"[trainer] Columns not found. Have: {list(df.columns)}", file=sys.stderr)
        sys.exit(3)

    X = df[[x_col]].values
    y = df[y_col].values

    # Train
    model = LinearRegression(fit_intercept=fit_intercept)
    model.fit(X, y)

    # Metrics (on full data, MVP)
    y_pred = model.predict(X)
    metrics: Dict[str, float | int] = {
        "r2": float(r2_score(y, y_pred)),
        "mse": float(mean_squared_error(y, y_pred)),
        "n_rows": int(len(y)),
        "fit_intercept": fit_intercept,
        "elapsed_sec": float(time.time() - t0),
    }

    # Save artifacts locally
    joblib.dump(model, local_model)
    with open(local_metrics, "w") as f:
        json.dump(metrics, f)

    # Write artifacts to outputs
    if out_model_url and out_metrics_url:
        print("[trainer] uploading artifacts via presigned URLs")
        upload_put(out_model_url, local_model, "application/octet-stream")
        upload_put(out_metrics_url, local_metrics, "application/json")
    elif output_dir:
        print(f"[trainer] writing artifacts under {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        os.replace(local_model, os.path.join(output_dir, "model.pkl"))
        os.replace(local_metrics, os.path.join(output_dir, "metrics.json"))
    else:
        print("[trainer] No output destination provided", file=sys.stderr)
        sys.exit(4)

    print("[trainer] done.")


if __name__ == "__main__":
    main()
