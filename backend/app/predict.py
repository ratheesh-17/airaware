# backend/app/predict.py
import joblib
from pathlib import Path
import numpy as np

MODEL_DIR = Path(__file__).resolve().parents[0] / "ml_model"
MODEL_PATH = MODEL_DIR / "aqi_rfr_multi.joblib"
FEATURES_PATH = MODEL_DIR / "feature_columns.txt"

_model = None
_feature_columns = None

def load_model():
    global _model, _feature_columns
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)

    if _feature_columns is None:
        if not FEATURES_PATH.exists():
            raise FileNotFoundError(f"Feature columns file not found: {FEATURES_PATH}")
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            _feature_columns = [line.strip() for line in f if line.strip()]

    return _model, _feature_columns

def predict_from_vector(vec):
    model, feature_cols = load_model()

    if len(vec) != len(feature_cols):
        raise ValueError(f"Expected {len(feature_cols)} features, got {len(vec)}")

    arr = np.array([vec], dtype=float)
    preds = model.predict(arr)

    result = preds[0]
    if hasattr(result, "tolist"):
        return result.tolist()
    else:
        return float(result)
