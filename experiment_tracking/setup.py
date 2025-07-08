import os
import mlflow
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database
import boto3
import json
from botocore.exceptions import ClientError
import argparse


def get_secret(secret_name, region_name="us-east-1"):
    """Retrieves a secret from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        print(f"Error getting secret: {e}")
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


def setup_mlflow_db(db_name, db_user, db_password, db_host, db_port):
    """Sets up the MLflow database schema using SQLAlchemy."""
    engine = None
    try:
        # Database URL for SQLAlchemy
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        # Create database if it doesn't exist
        if not database_exists(db_url):
            create_database(db_url)
            print(f"Database '{db_name}' created successfully.")

        # Connect to the database
        engine = create_engine(db_url)

        # Read and execute the init.sql file
        with engine.connect() as connection:
            with open("db/init.sql", "r") as f:
                # Execute multiline SQL script
                connection.execute(text(f.read()))
            connection.commit()
        print("MLflow schema created successfully.")

    except Exception as error:
        print(error)


def main():
    """Main function to set up and configure MLflow."""

    parser = argparse.ArgumentParser(description="Setup MLflow experiments.")
    parser.add_argument("--geography", type=str, help="Geography for the model variant (e.g., US, EU).")
    parser.add_argument("--company", type=str, help="Company for the model variant (e.g., ClientA).")
    args = parser.parse_args()

    # AWS Secrets Manager details from environment variables
    secret_name = os.getenv("MLFLOW_SECRET_NAME")
    secret_region = os.getenv("MLFLOW_SECRET_REGION", "us-east-1")

    # Database connection details from environment variables
    db_name = os.getenv("MLFLOW_DB_NAME", "mlflow_db")
    db_host = os.getenv("MLFLOW_DB_HOST", "localhost")
    db_port = os.getenv("MLFLOW_DB_PORT", "5432")

    # S3 bucket details from environment variables
    s3_bucket = os.getenv("MLFLOW_S3_BUCKET")

    if not all([secret_name, s3_bucket]):
        print("Please set the following environment variables:")
        print(" - MLFLOW_SECRET_NAME")
        print(" - MLFLOW_S3_BUCKET")
        return

    try:
        db_credentials = get_secret(secret_name, secret_region)
        db_user = db_credentials['username']
        db_password = db_credentials['password']
    except Exception as e:
        print(f"Failed to retrieve database credentials from AWS Secrets Manager: {e}")
        return

    # Set up the database
    setup_mlflow_db(db_name, db_user, db_password, db_host, db_port)

    # Set up the tracking URI
    tracking_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    mlflow.set_tracking_uri(tracking_uri)

    # Set up the artifact store
    artifact_root = f"s3://{s3_bucket}/"

    # Construct experiment name
    experiment_name = "churn_prediction"
    if args.geography:
        experiment_name += f"-geography-{args.geography.lower()}"
    if args.company:
        experiment_name += f"-company-{args.company.lower()}"

    try:
        experiment_id = mlflow.create_experiment(name=experiment_name, artifact_location=artifact_root)
        print(f"Experiment '{experiment_name}' created with ID: {experiment_id}")
    except Exception as e:
        print(f"Experiment '{experiment_name}' already exists.")
        experiment = mlflow.get_experiment_by_name(experiment_name)
        experiment_id = experiment.experiment_id

    print(f"Experiment '{experiment_name}' is ready to be used with ID: {experiment_id}")
    print(f"MLflow is configured to use the following tracking URI: {tracking_uri}")
    print(f"Artifacts for experiment '{experiment_name}' will be stored in: {artifact_root}")


if __name__ == "__main__":
    main()
