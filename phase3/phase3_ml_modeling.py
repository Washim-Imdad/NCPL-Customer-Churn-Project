"""
Phase 3: Machine Learning — Churn Prediction
Models: Logistic Regression, Random Forest, XGBoost
Metrics: Accuracy, Precision, Recall, F1, ROC-AUC
"""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEANED_CSV = PROJECT_ROOT / "output" / "phase1" / "cleaned_telco_churn.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "phase3"
MODELS_DIR = OUTPUT_DIR / "models"
FIGURES_DIR = OUTPUT_DIR / "figures"
PREDICTIONS_CSV = OUTPUT_DIR / "churn_predictions.csv"
METRICS_CSV = OUTPUT_DIR / "model_metrics.csv"

RANDOM_STATE = 42

# Exclude target, IDs, leakage, and raw text duplicates of encoded columns
EXCLUDE_COLS = {
    "CustomerID", "Churn Label", "Churn Value", "Churn_encoded",
    "Churn Score", "Churn Reason",  # leakage / post-churn
    "Country", "State", "City", "Zip Code", "Latitude", "Longitude",
    "Gender", "Senior Citizen", "Partner", "Dependents",
    "Phone Service", "Multiple Lines", "Internet Service",
    "Online Security", "Online Backup", "Device Protection",
    "Tech Support", "Streaming TV", "Streaming Movies",
    "Contract", "Paperless Billing", "Payment Method",
    "Tenure Group", "Payment Risk", "Risk Segment",
}

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["figure.dpi"] = 120


def load_dataset() -> pd.DataFrame:
    if not CLEANED_CSV.exists():
        raise FileNotFoundError(f"Run Phase 1 first. Missing: {CLEANED_CSV}")
    df = pd.read_csv(CLEANED_CSV)
    print(f"Loaded {len(df):,} rows from {CLEANED_CSV.name}")
    return df


def get_feature_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    X = df[feature_cols].copy()
    y = df["Churn_encoded"].copy()
    print(f"Features: {len(feature_cols)}")
    print(feature_cols)
    return X, y, feature_cols


def build_models() -> dict:
    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE, class_weight="balanced")),
        ]),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            n_jobs=-1,
        ),
    }
    if HAS_XGB:
        models["XGBoost"] = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
            eval_metric="logloss",
            scale_pos_weight=(5174 / 1869),  # handle imbalance
        )
    return models


def evaluate_model(name: str, model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    return {
        "model": name,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_prob), 4),
        "y_pred": y_pred,
        "y_prob": y_prob,
    }


def plot_confusion_matrix(y_test, y_pred, name: str, save: bool, display: bool) -> None:
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=["No Churn", "Churn"], yticklabels=["No Churn", "Churn"])
    ax.set_title(f"Confusion Matrix — {name}")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    path = FIGURES_DIR / f"confusion_matrix_{name.lower().replace(' ', '_')}.png"
    _finish_figure(fig, path, save, display)


def plot_roc_curves(results: list[dict], y_test, save: bool, display: bool) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    for r in results:
        fpr, tpr, _ = roc_curve(y_test, r["y_prob"])
        ax.plot(fpr, tpr, label=f"{r['model']} (AUC={r['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves — Model Comparison")
    ax.legend()
    path = FIGURES_DIR / "roc_curves_comparison.png"
    _finish_figure(fig, path, save, display)


def plot_feature_importance(model, feature_cols: list[str], name: str, save: bool, display: bool) -> None:
    if name == "Logistic Regression":
        clf = model.named_steps["clf"]
        importances = np.abs(clf.coef_[0])
    elif hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        return

    imp_df = pd.DataFrame({"feature": feature_cols, "importance": importances})
    imp_df = imp_df.sort_values("importance", ascending=True).tail(15)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(imp_df["feature"], imp_df["importance"], color=sns.color_palette("muted")[2])
    ax.set_title(f"Top 15 Feature Importance — {name}")
    ax.set_xlabel("Importance")
    path = FIGURES_DIR / f"feature_importance_{name.lower().replace(' ', '_')}.png"
    _finish_figure(fig, path, save, display)


def plot_shap_summary(model, X_test, feature_cols: list[str], save: bool, display: bool) -> None:
    if not HAS_SHAP:
        print("SHAP not installed — skipping SHAP plot.")
        return
    if "XGBoost" not in str(type(model)):
        print("SHAP summary shown for XGBoost best model only in this pipeline.")
        return

    explainer = shap.TreeExplainer(model)
    sample = X_test.sample(min(500, len(X_test)), random_state=RANDOM_STATE)
    shap_values = explainer.shap_values(sample)

    fig = plt.figure()
    shap.summary_plot(shap_values, sample, feature_names=feature_cols, show=False)
    plt.title("SHAP Summary — XGBoost")
    path = FIGURES_DIR / "shap_summary_xgboost.png"
    if save:
        plt.savefig(path, bbox_inches="tight")
    if display:
        plt.show()
    else:
        plt.close(fig)


def _finish_figure(fig, path: Path, save: bool, display: bool) -> None:
    fig.tight_layout()
    if save:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path)
    if display:
        plt.show()
    else:
        plt.close(fig)


def run_pipeline(*, save: bool = True, display: bool = False) -> pd.DataFrame:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if save:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = load_dataset()
    X, y, feature_cols = get_feature_target(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")

    models = build_models()
    results = []
    trained = {}

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        metrics = evaluate_model(name, model, X_test, y_test)
        results.append(metrics)
        trained[name] = model
        print(classification_report(y_test, metrics["y_pred"], target_names=["No Churn", "Churn"]))
        plot_confusion_matrix(y_test, metrics["y_pred"], name, save, display)
        plot_feature_importance(model, feature_cols, name, save, display)
        if save:
            joblib.dump(model, MODELS_DIR / f"{name.lower().replace(' ', '_')}.pkl")

    metrics_df = pd.DataFrame([{k: v for k, v in r.items() if k not in ("y_pred", "y_prob")} for r in results])
    metrics_df = metrics_df.sort_values("roc_auc", ascending=False)
    print("\n--- Model Comparison ---")
    print(metrics_df.to_string(index=False))

    if save:
        metrics_df.to_csv(METRICS_CSV, index=False)

    plot_roc_curves(results, y_test, save, display)

    best_name = metrics_df.iloc[0]["model"]
    best_model = trained[best_name]
    best_result = next(r for r in results if r["model"] == best_name)

    if best_name == "XGBoost":
        plot_shap_summary(best_model, X_test, feature_cols, save, display)

    predictions = df[["CustomerID", "Churn Label"]].copy()
    predictions["churn_probability"] = best_model.predict_proba(X)[:, 1]
    predictions["churn_prediction"] = (predictions["churn_probability"] >= 0.5).astype(int)
    predictions["model_used"] = best_name

    if save:
        predictions.to_csv(PREDICTIONS_CSV, index=False)
        print(f"\nSaved predictions to {PREDICTIONS_CSV}")
        print(f"Saved metrics to {METRICS_CSV}")
        print(f"Saved models to {MODELS_DIR}")

    return metrics_df


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Phase 3: ML churn prediction")
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    run_pipeline(save=not args.no_save, display=args.display)


if __name__ == "__main__":
    main()
