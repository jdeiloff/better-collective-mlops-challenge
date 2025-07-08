from dagster import asset, job, get_dagster_logger, Config, schedule, FreshnessPolicy, RetryPolicy
from dagster_aws.secrets import secretsmanager_resource

import pandas as pd
import os
import mlflow
import sqlalchemy
import json

class S3Config(Config):
    s3_bucket: str

class MLflowConfig(Config):
    mlflow_tracking_uri: str
    model_name: str
    model_stage: str = "Production"

class DBConfig(Config):
    db_secret_name: str

@asset
def raw_churn_data():
    """Fetches raw churn data from the data/churn folder."""
    # Correctly reference the data from the root of the project
    project_root = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(project_root, "data", "churn", "X_test_sample_2.json")
    feature_names_path = os.path.join(project_root, "data", "churn", "feature_names_3.json")

    with open(data_path, 'r') as f:
        data = json.load(f)
    with open(feature_names_path, 'r') as f:
        feature_names = json.load(f)

    return pd.DataFrame(data, columns=feature_names)

@asset
def transformed_features(raw_churn_data: pd.DataFrame) -> pd.DataFrame:
    """Applies feature transformations to the raw data."""
    # TODO: Add feature transformation logic here
    get_dagster_logger().info("Applying feature transformations (placeholder).")
    return raw_churn_data

@asset(required_resource_keys={"mlflow_config"})
def load_model_from_mlflow(context):
    """Loads the trained model artifact from MLflow."""
    mlflow_config = context.resources.mlflow_config
    mlflow.set_tracking_uri(mlflow_config.mlflow_tracking_uri)
    model_uri = f"models:/{mlflow_config.model_name}/{mlflow_config.model_stage}"
    get_dagster_logger().info(f"Loading model from {model_uri}")
    return mlflow.pyfunc.load_model(model_uri)

@asset
def generate_predictions(transformed_features: pd.DataFrame, model) -> pd.DataFrame:
    """Generates predictions using the loaded model."""
    predictions = model.predict(transformed_features)
    transformed_features['churn_probability'] = predictions
    # Assuming 'geography_id' is in the index or a column
    if 'geography_id' not in transformed_features.columns:
        transformed_features['geography_id'] = [f"GEO_{i}" for i in range(len(transformed_features))]
    return transformed_features[['geography_id', 'churn_probability']]

@asset(
    required_resource_keys={"db_config", "secretsmanager"},
    retry_policy=RetryPolicy(max_retries=3, delay=60)
)
def store_predictions(context, predictions: pd.DataFrame):
    """Stores the predictions in a PostgreSQL database."""
    db_config = context.resources.db_config
    secretsmanager = context.resources.secretsmanager

    secret_string = secretsmanager.get_secret_value(SecretId=db_config.db_secret_name)['SecretString']
    db_credentials = json.loads(secret_string)

    db_url = f"postgresql://{db_credentials['username']}:{db_credentials['password']}@{db_credentials['host']}:{db_credentials['port']}/{db_credentials['dbname']}"
    engine = sqlalchemy.create_engine(db_url)

    # Get model version from the loaded model if available
    # This is a placeholder as getting version from pyfunc is not straightforward
    model_version = "1.0.0" 

    predictions_to_store = predictions.copy()
    predictions_to_store['model_version'] = model_version

    with engine.connect() as connection:
        predictions_to_store.to_sql('churn_predictions', con=connection, if_exists='append', index=False)
        get_dagster_logger().info(f"Stored {len(predictions_to_store)} predictions in the database.")

@job
def churn_prediction_job():
    """Orchestrates the churn prediction pipeline."""
    predictions = generate_predictions(transformed_features(raw_churn_data()), load_model_from_mlflow())
    store_predictions(predictions)

@schedule(
    cron_schedule="0 0 * * 1",  # Every Monday at midnight UTC
    job=churn_prediction_job,
    execution_timezone="UTC",
)
def weekly_churn_prediction_schedule(context):
    """
    TODO add specific run config for the scheduled run to check for new data.
    """
    # A schedule that checks for new data and runs the churn prediction job weekly
    get_dagster_logger().info("Weekly churn prediction job scheduled.")
    return {}
