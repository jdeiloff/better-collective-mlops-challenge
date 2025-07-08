import os
import mlflow
import json
import pandas as pd
import xgboost as xgb
from mlflow.models.signature import infer_signature
import boto3
import tempfile
import argparse
from datetime import datetime

def main():
    """Logs the churn model and registers it in MLflow."""

    parser = argparse.ArgumentParser(description="Log a churn model to MLflow.")
    parser.add_argument("--geography", type=str, help="Geography for the model variant (e.g., US, EU).")
    parser.add_argument("--company", type=str, help="Company for the model variant (e.g., ClientA).")
    args = parser.parse_args()

    # MLflow tracking URI from environment variables
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        print("MLFLOW_TRACKING_URI environment variable not set.")
        return

    s3_bucket = os.getenv("MLFLOW_S3_BUCKET")
    if not s3_bucket:
        print("MLFLOW_S3_BUCKET environment variable not set.")
        return

    mlflow.set_tracking_uri(tracking_uri)

    # Construct experiment name
    experiment_name = "churn_prediction"
    if args.geography:
        experiment_name += f"-geography-{args.geography.lower()}"
    if args.company:
        experiment_name += f"-company-{args.company.lower()}"

    experiment = mlflow.get_experiment_by_name(experiment_name)
    if not experiment:
        print(f"Experiment '{experiment_name}' not found. Please create it first using setup.py.")
        return

    # Construct run name and tags
    run_name = "Model Logging"
    tags = {"training_date": datetime.now().strftime("%Y-%m-%d")}
    if args.geography:
        run_name += f" - Geo: {args.geography}"
        tags["geography"] = args.geography
    if args.company:
        run_name += f" - Company: {args.company}"
        tags["company_id"] = args.company

    with mlflow.start_run(experiment_id=experiment.experiment_id, run_name=run_name) as run:
        mlflow.set_tags(tags)

        # --- Load Model and Data from S3 ---
        s3_client = boto3.client('s3')

        # Parameterize S3 paths based on variants
        s3_base_path = ""
        if args.geography:
            s3_base_path += f"geography-{args.geography.lower()}/"
        if args.company:
            s3_base_path += f"company-{args.company.lower()}/"

        model_key = f"{s3_base_path}models/churn/xgb_churn_model_2.bin"
        features_key = f"{s3_base_path}data/churn/feature_names_3.json"
        sample_data_key = f"{s3_base_path}data/churn/X_test_sample_2.json"

        try:
            # Download model to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp_model_file:
                s3_client.download_file(s3_bucket, model_key, tmp_model_file.name)
                model_path = tmp_model_file.name

            # Load feature names from S3
            features_obj = s3_client.get_object(Bucket=s3_bucket, Key=features_key)
            feature_names = json.loads(features_obj['Body'].read().decode('utf-8'))

            # Load sample data from S3
            sample_data_obj = s3_client.get_object(Bucket=s3_bucket, Key=sample_data_key)
            sample_data = json.loads(sample_data_obj['Body'].read().decode('utf-8'))

        except Exception as e:
            print(f"Error loading artifacts from S3: {e}")
            return
        
        # Load model
        bst = xgb.Booster()
        bst.load_model(model_path)
        
        # Clean up temporary model file
        os.remove(model_path)

        input_df = pd.DataFrame(sample_data, columns=feature_names)
        
        # Create a dummy output for signature inference
        dummy_output = bst.predict(xgb.DMatrix(input_df))
        signature = infer_signature(input_df, dummy_output)

        # --- Log to MLflow ---
        print("Logging model, parameters, and metrics...")

        # Log parameters (using dummy values as an example)
        mlflow.log_params({
            "learning_rate": 0.1,
            "n_estimators": 100,
            "max_depth": 3
        })

        # Log metrics (using dummy values as an example)
        mlflow.log_metrics({
            "accuracy": 0.92,
            "precision": 0.85,
            "recall": 0.88
        })

        # Log the model
        registered_model_name = "churn-prediction-model"
        if args.geography:
            registered_model_name += f"-{args.geography.lower()}"
        if args.company:
            registered_model_name += f"-{args.company.lower()}"

        model_info = mlflow.xgboost.log_model(
            xgb_model=bst,
            artifact_path="churn_model",
            signature=signature,
            registered_model_name=registered_model_name
        )

        print(f"Model logged successfully to run ID: {run.info.run_id}")
        print(f"Model URI: {model_info.model_uri}")
        print(f"Model registered as version: {model_info.version}")

if __name__ == "__main__":
    main()
