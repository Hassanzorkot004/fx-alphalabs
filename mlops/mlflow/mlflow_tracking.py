"""
mlops/mlflow/mlflow_tracking.py
────────────────────────────────────────────────────────────────────────────
MLflow tracking integration for FX AlphaLab training.

Usage in train_agents_v3.py:
    from mlops.mlflow.mlflow_tracking import MLflowTracker
    
    tracker = MLflowTracker()
    with tracker.start_run("models_v4"):
        tracker.log_params({...})
        # ... training ...
        tracker.log_metrics({...})
        tracker.log_models("fx_alphalab/outputs/models_v4")
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


class MLflowTracker:

    def __init__(self, tracking_uri: str = None, experiment_name: str = "fx_alphalab"):
        if not MLFLOW_AVAILABLE:
            print("MLflow not installed — tracking disabled. Run: pip install mlflow")
            self.enabled = False
            return

        self.enabled = True
        uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(experiment_name)
        print(f"MLflow tracking: {uri} | experiment: {experiment_name}")

    @contextmanager
    def start_run(self, run_name: str):
        if not self.enabled:
            yield
            return
        with mlflow.start_run(run_name=run_name) as run:
            print(f"MLflow run started: {run.info.run_id}")
            yield run
            print(f"MLflow run completed: {run.info.run_id}")

    def log_params(self, params: Dict[str, Any]):
        if not self.enabled:
            return
        mlflow.log_params(params)

    def log_metrics(self, metrics: Dict[str, float], step: int = None):
        if not self.enabled:
            return
        mlflow.log_metrics(metrics, step=step)

    def log_models(self, models_dir: str):
        if not self.enabled:
            return
        models_path = Path(models_dir)
        if models_path.exists():
            mlflow.log_artifacts(str(models_path), artifact_path="models")
            print(f"MLflow: logged models from {models_path}")

    def log_backtest_results(self, results: Dict[str, float]):
        """Log backtest metrics after training."""
        if not self.enabled:
            return
        metrics = {
            f"backtest_{k}": v
            for k, v in results.items()
            if isinstance(v, (int, float))
        }
        mlflow.log_metrics(metrics)


# ── Example usage ─────────────────────────────────────────────────────────────

def example_training_with_mlflow():
    """
    Example of how to integrate MLflow into train_agents_v3.py
    Add this to your training script:
    """
    tracker = MLflowTracker()

    with tracker.start_run("models_v4_unified"):
        # Log hyperparameters
        tracker.log_params({
            "model_version":    "v4",
            "data_source":      "unified_matrix",
            "training_years":   10,
            "pairs":            "EURUSD,GBPUSD,USDJPY",
            "horizon_h":        12,
            "epochs":           60,
            "batch_size":       256,
            "learning_rate":    3e-4,
            "walk_forward_folds": 5,
            "llm_model":        "llama-3.1-8b-instant",
            "llm_provider":     "groq",
        })

        # ... your training code here ...

        # Log training metrics
        tracker.log_metrics({
            "eurusd_f1":        0.48,
            "gbpusd_f1":        0.46,
            "usdjpy_f1":        0.49,
            "avg_f1":           0.477,
        })

        # Log backtest results
        tracker.log_backtest_results({
            "win_rate":         0.698,
            "total_pips":       269.8,
            "profit_factor":    2.81,
            "max_drawdown":    -0.14,
            "sharpe":           32.46,
            "n_trades":         43,
        })

        # Log the trained models as artifacts
        tracker.log_models("fx_alphalab/outputs/models_v4")
