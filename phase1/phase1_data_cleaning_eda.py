"""
Phase 1: Data Cleaning, Feature Engineering & EDA
Customer Churn Prediction — Telco Dataset

Usage:
    python phase1/phase1_data_cleaning_eda.py              # save PNGs only
    python phase1/phase1_data_cleaning_eda.py --display    # show plots interactively
    python phase1/phase1_data_cleaning_eda.py --display --no-save
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "Data" / "Telco_customer_churn.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "output" / "phase1"
FIGURES_DIR = OUTPUT_DIR / "figures"
CLEANED_CSV = OUTPUT_DIR / "cleaned_telco_churn.csv"

SHEET_NAME = "Telco_Churn"

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["figure.dpi"] = 120


def load_data() -> pd.DataFrame:
    df = pd.read_excel(DATA_PATH, sheet_name=SHEET_NAME)
    print(f"Loaded {len(df):,} rows x {len(df.columns)} columns from {DATA_PATH.name}")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Drop redundant columns (constant or duplicate of other fields)
    drop_cols = ["Count", "Lat Long"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Remove duplicate rows / duplicate customer IDs
    dup_rows = df.duplicated().sum()
    dup_ids = df["CustomerID"].duplicated().sum()
    df = df.drop_duplicates()
    if dup_ids:
        df = df.drop_duplicates(subset="CustomerID", keep="first")
    print(f"Removed {dup_rows} duplicate rows, {dup_ids} duplicate CustomerIDs")

    # Fix Total Charges (stored as object; blank for tenure=0 new customers)
    df["Total Charges"] = pd.to_numeric(df["Total Charges"], errors="coerce")
    new_customer_mask = df["Total Charges"].isna() & (df["Tenure Months"] == 0)
    df.loc[new_customer_mask, "Total Charges"] = df.loc[new_customer_mask, "Monthly Charges"]
    remaining_na = df["Total Charges"].isna().sum()
    if remaining_na:
        df["Total Charges"] = df["Total Charges"].fillna(df["Total Charges"].median())

    # Churn Reason only exists for churned customers
    if "Churn Reason" in df.columns:
        df["Churn Reason"] = df["Churn Reason"].fillna("Not Applicable")

    # Strip whitespace from text columns
    obj_cols = df.select_dtypes(include=["object", "str"]).columns
    for col in obj_cols:
        df[col] = df[col].astype(str).str.strip()

    print(f"Missing values after cleaning:\n{df.isna().sum()[df.isna().sum() > 0]}")
    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    yes_no_cols = [
        "Gender",
        "Senior Citizen",
        "Partner",
        "Dependents",
        "Phone Service",
        "Paperless Billing",
    ]
    ternary_cols = [
        "Multiple Lines",
        "Online Security",
        "Online Backup",
        "Device Protection",
        "Tech Support",
        "Streaming TV",
        "Streaming Movies",
    ]

    binary_map = {"Yes": 1, "No": 0, "Male": 1, "Female": 0}
    for col in yes_no_cols:
        if col in df.columns:
            df[f"{col}_encoded"] = df[col].map(binary_map)

    ternary_map = {"Yes": 1, "No": 0, "No phone service": 0, "No internet service": 0}
    for col in ternary_cols:
        if col in df.columns:
            df[f"{col}_encoded"] = df[col].map(ternary_map)

    contract_map = {"Month-to-month": 0, "One year": 1, "Two year": 2}
    df["Contract_encoded"] = df["Contract"].map(contract_map)

    internet_map = {"No": 0, "DSL": 1, "Fiber optic": 2}
    df["Internet Service_encoded"] = df["Internet Service"].map(internet_map)

    payment_map = {
        "Electronic check": 0,
        "Mailed check": 1,
        "Bank transfer (automatic)": 2,
        "Credit card (automatic)": 3,
    }
    df["Payment Method_encoded"] = df["Payment Method"].map(payment_map)

    df["Churn_encoded"] = (df["Churn Label"] == "Yes").astype(int)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Tenure groups
    tenure_bins = [0, 12, 24, 48, np.inf]
    tenure_labels = ["0-12 months", "13-24 months", "25-48 months", "49+ months"]
    df["Tenure Group"] = pd.cut(
        df["Tenure Months"], bins=tenure_bins, labels=tenure_labels, right=True
    )

    # Average monthly spend (usage proxy)
    df["Avg Monthly Usage"] = df["Total Charges"] / df["Tenure Months"].replace(0, np.nan)
    df["Avg Monthly Usage"] = df["Avg Monthly Usage"].fillna(df["Monthly Charges"])

    # Count of add-on services subscribed
    service_encoded_cols = [
        c for c in df.columns if c.endswith("_encoded") and any(
            s in c for s in [
                "Online Security", "Online Backup", "Device Protection",
                "Tech Support", "Streaming TV", "Streaming Movies",
            ]
        )
    ]
    df["Service Count"] = df[service_encoded_cols].sum(axis=1)

    # Payment risk category
    def payment_risk(row: pd.Series) -> str:
        if (
            row["Contract"] == "Month-to-month"
            and row["Payment Method"] == "Electronic check"
            and row["Paperless Billing"] == "Yes"
        ):
            return "High"
        if row["Contract"] == "Month-to-month":
            return "Medium"
        return "Low"

    df["Payment Risk"] = df.apply(payment_risk, axis=1)

    # Customer segmentation by churn score
    df["Risk Segment"] = pd.cut(
        df["Churn Score"],
        bins=[0, 33, 66, 100],
        labels=["Low Risk", "Medium Risk", "High Risk"],
        include_lowest=True,
    )

    return df


def _finish_figure(fig, path: Path | None, *, save: bool, display: bool) -> None:
    fig.tight_layout()
    if save and path is not None:
        fig.savefig(path)
    if display:
        plt.show()
    else:
        plt.close(fig)


def run_eda(df: pd.DataFrame, *, save: bool = True, display: bool = False) -> None:
    if save:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    churn_counts = df["Churn Label"].value_counts()
    churn_rate = churn_counts.get("Yes", 0) / len(df)
    print("\n--- Churn Distribution ---")
    print(churn_counts)
    print(f"Overall churn rate: {churn_rate:.2%}")

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.countplot(data=df, x="Churn Label", hue="Churn Label", order=["No", "Yes"], ax=ax, legend=False)
    ax.set_title("Customer Churn Distribution")
    ax.set_xlabel("Churn")
    ax.set_ylabel("Number of Customers")
    for container in ax.containers:
        ax.bar_label(container, padding=3)
    _finish_figure(fig, FIGURES_DIR / "01_churn_distribution.png", save=save, display=display)

    # Churn by key segments
    segment_cols = ["Contract", "Internet Service", "Payment Risk", "Tenure Group"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, col in zip(axes.flat, segment_cols):
        pct = df.groupby(col, observed=True)["Churn_encoded"].mean().sort_values(ascending=False) * 100
        pct.plot(kind="bar", ax=ax, color=sns.color_palette("muted")[0])
        ax.set_title(f"Churn Rate by {col}")
        ax.set_ylabel("Churn Rate (%)")
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=25)
    _finish_figure(fig, FIGURES_DIR / "02_churn_by_segment.png", save=save, display=display)

    # Correlation heatmap (numeric + encoded features)
    corr_cols = [
        "Tenure Months",
        "Monthly Charges",
        "Total Charges",
        "Avg Monthly Usage",
        "Service Count",
        "Churn Score",
        "CLTV",
        "Churn_encoded",
        "Contract_encoded",
        "Internet Service_encoded",
        "Payment Method_encoded",
        "Partner_encoded",
        "Dependents_encoded",
        "Senior Citizen_encoded",
        "Paperless Billing_encoded",
    ]
    corr_cols = [c for c in corr_cols if c in df.columns]
    corr = df[corr_cols].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Feature Correlation Heatmap")
    _finish_figure(fig, FIGURES_DIR / "03_correlation_heatmap.png", save=save, display=display)

    # Feature importance — |correlation with churn| for all model-ready numeric features
    importance_cols = [
        "Tenure Months", "Monthly Charges", "Total Charges", "Avg Monthly Usage",
        "Service Count", "Churn Score", "CLTV",
        "Contract_encoded", "Internet Service_encoded", "Payment Method_encoded",
        "Partner_encoded", "Dependents_encoded", "Senior Citizen_encoded",
        "Paperless Billing_encoded", "Phone Service_encoded",
        "Multiple Lines_encoded", "Online Security_encoded", "Online Backup_encoded",
        "Device Protection_encoded", "Tech Support_encoded",
        "Streaming TV_encoded", "Streaming Movies_encoded", "Gender_encoded",
    ]
    importance_cols = [c for c in importance_cols if c in df.columns]
    importance = (
        df[importance_cols + ["Churn_encoded"]]
        .corr(numeric_only=True)["Churn_encoded"]
        .drop("Churn_encoded")
        .abs()
        .sort_values(ascending=True)
    )
    print("\n--- Feature Importance (|correlation with churn|) — all numeric/encoded features ---")
    print(importance.sort_values(ascending=False).to_string())

    fig, ax = plt.subplots(figsize=(10, 8))
    importance.plot(kind="barh", ax=ax, color=sns.color_palette("muted")[2])
    ax.set_title("Feature Importance (|Correlation with Churn|)\nAll numeric & encoded features")
    ax.set_xlabel("Absolute Correlation")
    _finish_figure(fig, FIGURES_DIR / "04_feature_importance.png", save=save, display=display)

    # Payment risk segmentation
    risk_summary = (
        df.groupby("Payment Risk", observed=True)
        .agg(customers=("CustomerID", "count"), churn_rate=("Churn_encoded", "mean"))
        .sort_values("churn_rate", ascending=False)
    )
    risk_summary["churn_rate"] = (risk_summary["churn_rate"] * 100).round(1)
    print("\n--- Customer Segmentation by Payment Risk ---")
    print(risk_summary)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(
        data=risk_summary.reset_index(),
        x="Payment Risk",
        y="churn_rate",
        hue="Payment Risk",
        order=["High", "Medium", "Low"],
        hue_order=["High", "Medium", "Low"],
        ax=ax,
        palette="Reds_r",
        legend=False,
    )
    ax.set_title("Churn Rate by Payment Risk Category")
    ax.set_ylabel("Churn Rate (%)")
    ax.set_xlabel("Payment Risk")
    _finish_figure(fig, FIGURES_DIR / "05_payment_risk_churn.png", save=save, display=display)

    # Tenure vs Monthly Charges scatter colored by churn
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=df.sample(min(2000, len(df)), random_state=42),
        x="Tenure Months",
        y="Monthly Charges",
        hue="Churn Label",
        alpha=0.5,
        ax=ax,
    )
    ax.set_title("Tenure vs Monthly Charges (sample)")
    _finish_figure(fig, FIGURES_DIR / "06_tenure_vs_charges.png", save=save, display=display)

    if save:
        print(f"\nSaved figures to {FIGURES_DIR}")
    if display:
        print("\nDisplayed all EDA plots (close each window to continue).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1: Data cleaning, EDA, and feature engineering")
    parser.add_argument("--display", action="store_true", help="Show plots interactively (plt.show)")
    parser.add_argument("--no-save", action="store_true", help="Skip saving PNG files")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df_raw = load_data()
    print("\n--- Raw Data Summary ---")
    print(df_raw.describe(include="all").transpose()[["count", "unique", "mean", "min", "max"]].head(15))

    df_clean = clean_data(df_raw)
    df_features = engineer_features(encode_categoricals(df_clean))

    run_eda(df_features, save=not args.no_save, display=args.display)

    df_features.to_csv(CLEANED_CSV, index=False)
    print(f"\nSaved cleaned dataset ({len(df_features):,} rows) to:\n  {CLEANED_CSV}")


if __name__ == "__main__":
    main()
