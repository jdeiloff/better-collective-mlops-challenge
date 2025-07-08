# Orchestration with Dagster

This directory contains the Dagster implementation for orchestrating the churn prediction pipeline.

## Features

The Dagster job is designed to:

*   Fetch raw input data from the S3 artifact store (using the `MLFLOW_S3_BUCKET` environment variable) and fall back to the local `data/churn` folder if S3 is unavailable or the fetch fails.
*   Apply feature transformations (with a placeholder for future implementation).
*   Load the trained model artifact from an MLflow server.
*   Generate predictions on the data.
*   Store the predictions in a PostgreSQL database.
*   Run on a weekly schedule.
*   Include retry logic for critical steps to enhance robustness.
*   Provide a placeholder for logic to detect new data availability.

## File Structure

*   **`job.py`**: Defines the main Dagster assets and the prediction job. It includes the logic for each step of the pipeline, the weekly schedule, and the retry policy. The `raw_churn_data` asset now attempts to fetch from S3 first, then falls back to local files if S3 is unavailable or fails.
*   **`requirements.txt`**: Lists the Python dependencies required to run the Dagster job.
*   **`config/dagster.yaml`**: A configuration file for setting up the necessary resources, such as the MLflow tracking URI and database connection details.
*   **`db/init.sql`**: SQL script to create the table for storing predictions.

## Setup and Configuration

1.  **Install Dependencies**:

    ```bash
    pip install -r orchestration/requirements.txt
    ```

2.  **Configure Resources**:

    Edit the `orchestration/config/dagster.yaml` file to provide the necessary configurations for your environment:

    *   `mlflow_tracking_uri`: The URI for your MLflow tracking server.
    *   `db_secret_name`: The name of the AWS Secret containing your database credentials.
    *   `region_name`: The AWS region where your secret is stored.
    *   `MLFLOW_S3_BUCKET`: The S3 bucket name (set as an environment variable).

## Running the Job

To run the Dagster job locally and view it in the Dagster UI, you can use the following command from the root of the repository:

```bash
dagster dev -f orchestration/job.py
```

This will start the Dagster UI, where you can inspect the job, trigger runs manually, and view the schedule.
