# Experiment Tracking with MLflow

This directory contains the scripts for setting up and interacting with the MLflow tracking environment for the churn prediction model.

## Installation

This project uses `uv` for dependency management. To install the required packages, ensure you have `uv` installed and then run the following command from the root of the `experiment_tracking` directory:

```bash
uv pip install -r requirements.txt
```

## Setup

Before running the scripts, you need to configure the environment.

### Prerequisites

1.  **PostgreSQL Server**: A running instance of PostgreSQL to be used as the MLflow backend store.
2.  **AWS S3 Bucket**: An S3 bucket to store MLflow artifacts.
3.  **AWS Secrets Manager**: A secret in AWS Secrets Manager containing the PostgreSQL credentials in the following JSON format:
    ```json
    {"username": "your-user", "password": "your-password"}
    ```

### Environment Variables

Export the following environment variables in your terminal:

```bash
# Required for setup.py and log_model.py
export MLFLOW_SECRET_NAME="your_secret_name"
export MLFLOW_S3_BUCKET="your_s3_bucket_name"

# Required for log_model.py
export MLFLOW_TRACKING_URI="postgresql://<user>:<password>@<host>:<port>/<db_name>"

# Optional - Default values are provided in the scripts
export MLFLOW_DB_NAME="mlflow_db"
export MLFLOW_DB_HOST="localhost"
export MLFLOW_DB_PORT="5432"
export MLFLOW_SECRET_REGION="us-east-1"
```

## Usage

### 1. Setting up the MLflow Experiment

The `setup.py` script initializes the database schema and creates MLflow experiments.

*   **To create the default experiment:**

    ```bash
    python setup.py
    ```
    This will create an experiment named `churn_prediction`.

*   **To create experiments for model variants:**

    You can create separate experiments for different model variants (e.g., by geography or company) using optional command-line arguments.

    ```bash
    # For a specific geography
    python setup.py --geography US

    # For a specific company
    python setup.py --company ClientA

    # For a combination
    python setup.py --geography EU --company ClientB
    ```
    This will create experiments with names like `churn_prediction-geography-us` or `churn_prediction-geography-eu-company-clientb`.

### 2. Logging and Registering a Model

The `log_model.py` script logs a model to the specified experiment and registers it in the MLflow Model Registry. It sources the model artifacts from a corresponding path in the S3 bucket.

**S3 Artifact Structure:**

Before logging a model variant, ensure its artifacts are uploaded to the correct path in your S3 bucket. The path is constructed based on the variant arguments.

*   **Base model:** `s3://<bucket>/models/churn/` and `s3://<bucket>/data/churn/`
*   **Geography variant:** `s3://<bucket>/geography-us/models/churn/`
*   **Company variant:** `s3://<bucket>/company-clienta/models/churn/`

**To run the script:**

*   **To log the base model:**

    ```bash
    python log_model.py
    ```

*   **To log a model variant:**

    Use the same optional arguments as the `setup.py` script.

    ```bash
    # Log a model for a specific geography
    python log_model.py --geography US

    # Log a model for a specific company and geography
    python log_model.py --geography EU --company ClientB
    ```

This will log a run to the corresponding experiment, tag it with the variant details, and register a versioned model with a name like `churn-prediction-model-us`.
