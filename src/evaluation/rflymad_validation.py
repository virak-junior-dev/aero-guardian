"""
RFlyMAD / ALFA Deterministic Validation
=======================================
Author: AeroGuardian Member
Date: 2026-03-12

Validates AeroGuardian's deterministic anomaly detection logic against
the REAL ALFA/RFlyMAD dataset (alfa_cleaned.csv).

STATISTICAL GROUNDING:
    Thresholds are derived from 3-sigma (Z-score > 3) bounds of the
    ALFA normal-flight distribution. This aligns with the DO-178C
    philosophy of traceable, mathematically justified decision logic.

OUTPUTS:
    1. reports/rflymad_real_confusion_matrix.png  -- Confusion matrix heatmap
    2. reports/rflymad_f1_bar_chart.png           -- Per-class F1 bar chart
    3. reports/rflymad_detailed_metrics.csv        -- Per-window predictions
    4. reports/rflymad_summary_metrics.csv         -- Per-class + macro metrics

USAGE:
    python src/evaluation/rflymad_validation.py
"""

import logging
import math
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/CI environments
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("AeroGuardian.RFlyMADValidation")

# =========================================================================
# CONSTANTS
# =========================================================================

# Subsystem classes for classification
CLASSES = ["Navigation", "Propulsion/Control", "Nominal"]

# Telemetry window size (samples per evaluation chunk)
WINDOW_SIZE = 100

# Fault-type column value in ALFA dataset
ALFA_FAULT_COLUMN = "is_fault"
ALFA_FAULT_TYPE_COLUMN = "fault_type"
ALFA_FLIGHT_ID_COLUMN = "flight_id"
ALFA_TIMESTAMP_COLUMN = "timestamp"


# =========================================================================
# 3-SIGMA BASELINE COMPUTATION
# =========================================================================

def compute_baseline_statistics(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Compute mean (mu) and standard deviation (sigma) for each sensor
    channel from NORMAL (non-fault) flight data only.

    These statistics define the 3-sigma anomaly thresholds:
        threshold = mu + 3 * sigma

    This fulfills the methodology commitment: "cite that we processed
    the RFlyMAD normal flight dataset to find mu and sigma of a healthy
    quadcopter."

    Args:
        df: Full ALFA DataFrame with is_fault column.

    Returns:
        Dictionary mapping channel names to {mu, sigma, threshold_3s}.
    """
    normal_data = df[df[ALFA_FAULT_COLUMN] == 0]
    total_normal = len(normal_data)

    if total_normal == 0:
        logger.error(">>>>> No normal flight data found. Cannot compute baselines.")
        raise ValueError("ALFA dataset contains no normal flight samples.")

    logger.info(
        f">>>>> Computing 3-sigma baselines from {total_normal:,} "
        f"normal-flight samples..."
    )

    channels = ["vel_x", "vel_y", "vel_z", "gyro_x", "gyro_y", "gyro_z"]
    baselines = {}

    for channel in channels:
        if channel not in normal_data.columns:
            logger.warning(f">>>>> Channel '{channel}' not found in dataset. Skipping.")
            continue

        values = normal_data[channel].abs()
        mu = float(values.mean())
        sigma = float(values.std())
        threshold = mu + 3.0 * sigma

        baselines[channel] = {
            "mu": mu,
            "sigma": sigma,
            "threshold_3s": threshold,
        }

        logger.info(
            f"     {channel:<8} | mu={mu:.4f} | sigma={sigma:.4f} "
            f"| 3-sigma threshold={threshold:.4f}"
        )

    return baselines


# =========================================================================
# DETERMINISTIC CLASSIFICATION
# =========================================================================

def classify_window(
    chunk: pd.DataFrame,
    baselines: Dict[str, Dict[str, float]],
) -> Tuple[str, str, Dict[str, float]]:
    """
    Classify a single telemetry window using 3-sigma thresholds.

    Decision logic (priority order):
        1. Propulsion failure: vel_z exceeds its 3-sigma bound
        2. Control failure: gyro_x or gyro_y exceeds 3-sigma bound
        3. Navigation failure: vel_x or vel_y exceeds 3-sigma bound
        4. Nominal: no thresholds exceeded

    Args:
        chunk: DataFrame slice of one telemetry window.
        baselines: 3-sigma baselines from compute_baseline_statistics().

    Returns:
        Tuple of (true_label, pred_label, raw_features_dict).
    """
    # --- Ground truth label ---
    if chunk[ALFA_FAULT_COLUMN].sum() > 0:
        true_label = "Propulsion/Control"  # ALFA dataset fault = engine_failure, which causes loss of control and lift
    else:
        true_label = "Nominal"

    # --- Feature extraction ---
    max_vel_z = float(chunk["vel_z"].abs().max())
    max_vel_xy = float(max(chunk["vel_x"].abs().max(), chunk["vel_y"].abs().max()))
    max_gyro_xy = float(max(chunk["gyro_x"].abs().max(), chunk["gyro_y"].abs().max()))
    max_gyro_z = float(chunk["gyro_z"].abs().max())

    raw_features = {
        "max_vel_z": max_vel_z,
        "max_vel_xy": max_vel_xy,
        "max_gyro_xy": max_gyro_xy,
        "max_gyro_z": max_gyro_z,
    }

    # --- Deterministic classification using 3-sigma bounds ---
    vel_z_threshold = baselines.get("vel_z", {}).get("threshold_3s", 4.5)
    gyro_x_threshold = baselines.get("gyro_x", {}).get("threshold_3s", 3.0)
    gyro_y_threshold = baselines.get("gyro_y", {}).get("threshold_3s", 3.0)
    gyro_z_threshold = baselines.get("gyro_z", {}).get("threshold_3s", 2.5)
    vel_x_threshold = baselines.get("vel_x", {}).get("threshold_3s", 10.0)
    vel_y_threshold = baselines.get("vel_y", {}).get("threshold_3s", 10.0)

    pred_label = "Nominal"

    # Priority 1: Propulsion/Control -- extreme vertical velocity OR extreme rotational rates
    if max_vel_z > vel_z_threshold or max_gyro_xy > max(gyro_x_threshold, gyro_y_threshold) or max_gyro_z > gyro_z_threshold:
        pred_label = "Propulsion/Control"

    # Priority 2: Navigation -- extreme horizontal velocity (flyaway) WITHOUT extreme rotation
    elif max_vel_xy > max(vel_x_threshold, vel_y_threshold):
        pred_label = "Navigation"

    return true_label, pred_label, raw_features


def generate_real_predictions(
    csv_path: str,
) -> Tuple[List[str], List[str], pd.DataFrame]:
    """
    Load the real ALFA dataset, compute 3-sigma baselines from normal
    flights, then classify every telemetry window.

    Args:
        csv_path: Absolute path to alfa_cleaned.csv.

    Returns:
        Tuple of (y_true, y_pred, detailed_df) where detailed_df has
        per-window metadata for CSV export.
    """
    logger.info(f">>>>> Loading real telemetry data from {csv_path}...")
    df = pd.read_csv(csv_path)

    logger.info(
        f">>>>> Dataset loaded: {len(df):,} rows, "
        f"{df[ALFA_FLIGHT_ID_COLUMN].nunique()} flights"
    )

    # Step 1: Compute 3-sigma baselines from normal flight data
    baselines = compute_baseline_statistics(df)

    # Step 2: Classify each window
    logger.info(
        f">>>>> Classifying {WINDOW_SIZE}-sample windows with "
        f"3-sigma deterministic thresholds..."
    )

    y_true: List[str] = []
    y_pred: List[str] = []
    detail_rows: List[Dict] = []

    for flight_id, group in df.groupby(ALFA_FLIGHT_ID_COLUMN):
        group = group.sort_values(by=ALFA_TIMESTAMP_COLUMN)
        num_chunks = max(1, len(group) // WINDOW_SIZE)

        for i in range(num_chunks):
            chunk = group.iloc[i * WINDOW_SIZE : (i + 1) * WINDOW_SIZE]
            if len(chunk) < WINDOW_SIZE // 2:
                continue  # Skip very short tail chunks

            true_label, pred_label, features = classify_window(chunk, baselines)

            y_true.append(true_label)
            y_pred.append(pred_label)

            detail_rows.append({
                "window_id": f"{flight_id}_w{i}",
                "flight_id": flight_id,
                "window_index": i,
                "num_samples": len(chunk),
                "true_label": true_label,
                "predicted_label": pred_label,
                "is_correct": true_label == pred_label,
                "fault_samples_in_window": int(chunk[ALFA_FAULT_COLUMN].sum()),
                **features,
            })

    detailed_df = pd.DataFrame(detail_rows)
    return y_true, y_pred, detailed_df


# =========================================================================
# METRICS CALCULATION (NO SCIKIT-LEARN)
# =========================================================================

def calculate_metrics(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str],
) -> Tuple[List[List[int]], Dict[str, Dict[str, float]]]:
    """
    Deterministically calculate confusion matrix and per-class metrics.

    Implements Precision, Recall, F1-Score, Accuracy using only basic
    arithmetic. No external ML libraries. Fully DO-178C traceable.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted labels.
        labels: Ordered list of class names.

    Returns:
        Tuple of (confusion_matrix_2d_list, metrics_dict).
    """
    n_classes = len(labels)
    cm = [[0] * n_classes for _ in range(n_classes)]
    label_to_idx = {label: i for i, label in enumerate(labels)}

    for true_label, pred_label in zip(y_true, y_pred):
        true_idx = label_to_idx.get(true_label)
        pred_idx = label_to_idx.get(pred_label)
        if true_idx is not None and pred_idx is not None:
            cm[true_idx][pred_idx] += 1

    total_samples = len(y_true)
    total_correct = sum(cm[i][i] for i in range(n_classes))

    metrics: Dict[str, Dict[str, float]] = {}

    for i, label in enumerate(labels):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(n_classes) if j != i)
        fn = sum(cm[i][j] for j in range(n_classes) if j != i)
        tn = total_samples - (tp + fp + fn)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (tp + tn) / total_samples if total_samples > 0 else 0.0

        metrics[label] = {
            "Precision": precision,
            "Recall": recall,
            "F1-Score": f1,
            "Accuracy": accuracy,
            "Support": tp + fn,
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "TN": tn,
        }

    # Macro averages (only over classes with support > 0 or predictions > 0)
    active = [
        l for l in labels
        if metrics[l]["Support"] > 0
        or sum(cm[j][label_to_idx[l]] for j in range(n_classes)) > 0
    ]
    n_active = max(len(active), 1)

    metrics["Macro_Average"] = {
        "Precision": sum(metrics[l]["Precision"] for l in active) / n_active,
        "Recall": sum(metrics[l]["Recall"] for l in active) / n_active,
        "F1-Score": sum(metrics[l]["F1-Score"] for l in active) / n_active,
        "Accuracy": total_correct / total_samples if total_samples > 0 else 0.0,
        "Support": total_samples,
        "TP": sum(metrics[l]["TP"] for l in labels),
        "FP": sum(metrics[l]["FP"] for l in labels),
        "FN": sum(metrics[l]["FN"] for l in labels),
        "TN": sum(metrics[l]["TN"] for l in labels),
    }

    return cm, metrics


# =========================================================================
# VISUALIZATION
# =========================================================================

def plot_confusion_matrix(
    cm: List[List[int]],
    labels: List[str],
    output_path: Path,
) -> None:
    """Generate publication-quality confusion matrix heatmap."""
    plt.figure(figsize=(10, 8))
    sns.set_theme(style="whitegrid", font_scale=1.2)

    ax = sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        linewidths=0.5,
        cbar_kws={"label": "Number of Samples"},
    )

    plt.title(
        "AeroGuardian Deterministic Anomaly Classification\n"
        "(Real ALFA Dataset | 3-Sigma Thresholds)",
        pad=20, fontsize=16, fontweight="bold",
    )
    plt.xlabel("Predicted Subsystem", labelpad=15, fontsize=14, fontweight="bold")
    plt.ylabel("True Subsystem", labelpad=15, fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f">>>>> Saved confusion matrix: {output_path}")


def plot_f1_bar_chart(
    metrics: Dict[str, Dict[str, float]],
    labels: List[str],
    output_path: Path,
) -> None:
    """Generate per-class F1-score bar chart for DASC paper."""
    active_labels = [l for l in labels if metrics[l]["Support"] > 0]
    f1_scores = [metrics[l]["F1-Score"] for l in active_labels]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(active_labels, f1_scores, color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"])

    for bar, score in zip(bars, f1_scores):
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.01,
            f"{score:.3f}",
            ha="center", va="bottom", fontsize=13, fontweight="bold",
        )

    macro_f1 = metrics["Macro_Average"]["F1-Score"]
    plt.axhline(y=macro_f1, color="red", linestyle="--", linewidth=1.5, label=f"Macro F1 = {macro_f1:.3f}")
    plt.legend(fontsize=12)

    plt.title(
        "Per-Class F1-Score (3-Sigma Deterministic Detection)",
        fontsize=16, fontweight="bold", pad=15,
    )
    plt.xlabel("Subsystem Class", fontsize=14, fontweight="bold", labelpad=10)
    plt.ylabel("F1-Score", fontsize=14, fontweight="bold", labelpad=10)
    plt.ylim(0, 1.1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f">>>>> Saved F1 bar chart: {output_path}")


# =========================================================================
# CSV EXPORT
# =========================================================================

def export_detailed_csv(
    detailed_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Export per-window predictions with raw features to CSV."""
    detailed_df.to_csv(output_path, index=False, float_format="%.6f")
    logger.info(
        f">>>>> Saved detailed metrics CSV ({len(detailed_df)} rows): "
        f"{output_path}"
    )


def export_summary_csv(
    metrics: Dict[str, Dict[str, float]],
    labels: List[str],
    output_path: Path,
) -> None:
    """Export per-class + macro-average metrics to CSV."""
    rows = []

    for label in labels:
        m = metrics[label]
        rows.append({
            "Class": label,
            "Precision": round(m["Precision"], 6),
            "Recall": round(m["Recall"], 6),
            "F1-Score": round(m["F1-Score"], 6),
            "Accuracy": round(m["Accuracy"], 6),
            "Support": int(m["Support"]),
            "TP": int(m["TP"]),
            "FP": int(m["FP"]),
            "FN": int(m["FN"]),
            "TN": int(m["TN"]),
        })

    macro = metrics["Macro_Average"]
    rows.append({
        "Class": "MACRO_AVERAGE",
        "Precision": round(macro["Precision"], 6),
        "Recall": round(macro["Recall"], 6),
        "F1-Score": round(macro["F1-Score"], 6),
        "Accuracy": round(macro["Accuracy"], 6),
        "Support": int(macro["Support"]),
        "TP": int(macro["TP"]),
        "FP": int(macro["FP"]),
        "FN": int(macro["FN"]),
        "TN": int(macro["TN"]),
    })

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_path, index=False)
    logger.info(f">>>>> Saved summary metrics CSV: {output_path}")


# =========================================================================
# MAIN
# =========================================================================

def main() -> None:
    """Execute the full ALFA/RFlyMAD deterministic validation pipeline."""
    logger.info("=" * 70)
    logger.info("  AEROGUARDIAN ALFA/RFLYMAD REAL DATA VALIDATION")
    logger.info("  3-Sigma Statistical Thresholds | NO Scikit-Learn")
    logger.info("=" * 70)

    # --- Paths ---
    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / "data" / "raw" / "alfa" / "alfa_cleaned.csv"
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    cm_path = reports_dir / "rflymad_real_confusion_matrix.png"
    f1_path = reports_dir / "rflymad_f1_bar_chart.png"
    detail_csv_path = reports_dir / "rflymad_detailed_metrics.csv"
    summary_csv_path = reports_dir / "rflymad_summary_metrics.csv"

    if not data_path.exists():
        logger.error(f"Dataset not found at {data_path}. Aborting.")
        return

    # --- 1. Generate predictions from real data ---
    y_true, y_pred, detailed_df = generate_real_predictions(str(data_path))
    logger.info(f">>>>> Evaluated {len(y_true)} telemetry windows.")

    # --- 2. Calculate metrics ---
    logger.info(">>>>> Calculating deterministic metrics (NO Scikit-Learn)...")
    cm, metrics = calculate_metrics(y_true, y_pred, CLASSES)

    # --- 3. Print results ---
    header = (
        f"{'CLASS':<15} | {'PRECISION':<10} | {'RECALL':<10} "
        f"| {'F1-SCORE':<10} | {'SUPPORT':<10}"
    )
    logger.info("")
    logger.info(header)
    logger.info("-" * 65)

    for cls in CLASSES:
        m = metrics[cls]
        logger.info(
            f"{cls:<15} | {m['Precision']:.4f}     | {m['Recall']:.4f}   "
            f"| {m['F1-Score']:.4f}   | {int(m['Support'])}"
        )

    logger.info("-" * 65)
    macro = metrics["Macro_Average"]
    logger.info(
        f"{'MACRO AVERAGE':<15} | {macro['Precision']:.4f}     "
        f"| {macro['Recall']:.4f}   | {macro['F1-Score']:.4f}   "
        f"| {int(macro['Support'])}"
    )
    logger.info("=" * 70)

    # --- 4. Save plots ---
    plot_confusion_matrix(cm, CLASSES, cm_path)
    plot_f1_bar_chart(metrics, CLASSES, f1_path)

    # --- 5. Export CSV reports ---
    export_detailed_csv(detailed_df, detail_csv_path)
    export_summary_csv(metrics, CLASSES, summary_csv_path)

    logger.info("")
    logger.info(">>>>> REAL Data Validation complete.")
    logger.info(f">>>>> Outputs saved to: {reports_dir}")


if __name__ == "__main__":
    main()
