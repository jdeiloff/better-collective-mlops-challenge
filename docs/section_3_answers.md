# 1. Model Serving Strategy

## Would you serve this model in real-time or batch? Justify your decision.

I would serve this model in batch. Churning is a process that ocurrs over time, it is not an instant event. The objective of these models is to target users at risk of being lost with some kind of targeted approach like retention campaigns, special offers, free credits, etc. This is generally planned and discussed with many stakeholders, is not spontaneous so a weekly rate is enough.

Taking the nature of the data itself, it also does not make too much sense to use real-time serving for this model, as the data is being generated through batch ETL data engineering processes maybe daily or weekly, and this cadence is a limiter to the model serving strategy, serving it real time for weekly updated data does not make any sense.

Regarding the infrastructure, it is expensive and complex to maintain a real-time inference endpoint for a problem where predictions are not needed instantly, if the business value and the data nature do not enable taking this hard route, it's better to evade it, batch processing is the balanced approach.

## If real-time: How would you containerize and expose the model?

It is not the case here, but assuming that real-time inference is a must to have requirement, I would implement a script that is containerized having an API application with its required dependencies (uvicorn, fastapi, mlflow, xgboost, etc) with the required environments and uvicorn server commands to run it. 

Specifically for the API, I would use FastAPI as it is performant, has plenty of documentation and samples and is able to enforce the model's input schema using Pydantic (even GCP's Vertex uses it for serving its models as a backend). 

The application would load the production model from the MLFlow Model Registry, pulling the model version related to the required churn model version.

Fos the deployment, it is possible to use AWS ECS with Fargate or similar services like GKE and CloudRun or AKE and Azure Functions. All approaches are similar, they enable to do an exposure in a serverless environment, easy to orchestrate using other tools like Dagster or even a cron schedule, taking care of traffic, distribute requests, authentication and scalability.

You can also prevent all the containerized approach and directly using AWS SageMaker for the exposure in an endpoint, using mlflow.sagemaker to deploy the registered model directly even from a Jupyter Notebook without taking care of the whole infrastructure mentioned before (and maybe not needing an MLOps engineer!) (don't read this).

## If batch: How would you manage versioned batch scoring jobs?

Using MLFlow (like this proposed solution offers). The Model Registry is the source of truth for the model versioning, it allows to assign different stages to each version (staging, production, archived). It is possible to dynamically load the models in the orchestrator (in this proposal, using Dagster), taking the latest model with the requested tag from MLFlow Registry associated with the stage for that model_name. For each run, the orchestrator loads the model, retrieves its metadata that can be added to the final prediction output (in this proposal, saved into a PostgreSQL DB) to correctly record the lineage of the prediction and have a table for it with the required metrics, timestamps, model name and version. Dagster creates a visual queryable line graph that helps with the documentation lineage and can also be tagged for more traceability.

# 2. CI/CD and Infrastructure as Code (IaC)

## How would you structure the CI/CD pipelines for this system?

If the time is a limitant and the requirement must be achieved as fast as possible, a monolithic pipeline is the fastest working approach. But with time and resources, the ideal way would be creating three distinct independant pipelines that can be triggered by an orchestrator and reused for other purposes:
 
 - The model training pipeline: Can be triggered on push to the main branch when affecting model-related files of this proposed solution , the objective is to automate the training, validation, logging and registration of each new model candidate to only register validated high-quality and score models would got into the MLFlow Registry. Can be made using a Dagster job.

 - Orchestration Pipeline: Triggered on push to the main branch affecting orchestration files, to test, package and deploy the Dagster jobs required to do the batch prediction jobs without the retraining of the models

 - Infrastructure pipeline: Triggered on push affecting the infrastructure files. To plan and apply the changes in the cloud infrastructure. For production, it requires a manual approval to prevent any loop or potential issue deploying unneeded services in the cloud provider.

## What kind of GitHub Actions steps would you include? 

After setting up the required accesses tokens, a .yml file in the .github/workflows/ directory would be able to automate each of the previously explained steps, here is a sample .yml file for the orchestration pipeline:

```yaml
name: Orchestration CI/CD

on:
  push:
    branches: [ main ]
    paths:
      - 'orchestration/**'

jobs:
  build_and_deploy_dagster_code:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Log in to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, Tag, and Push Docker Image to ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: dagster-user-code
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG -f orchestration/Dockerfile .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Reload Dagster Deployment (Example for Dagster Cloud)
        env:
          DAGSTER_CLOUD_API_TOKEN: ${{ secrets.DAGSTER_CLOUD_API_TOKEN }}
        run: |
          # This step tells Dagster to use the new image
          dagster-cloud workspace-agent-reload --url "https://<bc-aws>.dagster.cloud/<deployment>"
```

## Provide a terraform/folder structure or snippet showing how you would provision:
* MlFlow backend (PostgreSQL metadata store + S3 artifact store)
* Compute for orchestration (ECS/Fargate or EKS)

 And as Terraform is mentioned and maybe used in the company, here below is a sample folder structure for the provision:

```
terraform/
├── modules/
│   ├── mlflow_backend/
│   │   ├── main.tf         # S3, RDS, Secrets Manager, Security Group
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── dagster_compute/
│       ├── main.tf         # ECS Cluster, IAM Roles for tasks
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── dev/
    │   ├── main.tf         # Calls the modules for the dev environment
    │   ├── backend.tf      # S3 backend config for dev statefile
    │   └── terraform.tfvars
    └── prod/
        ├── main.tf         # Calls the modules for the prod environment
        ├── backend.tf      # S3 backend config for prod statefile
        └── terraform.tfvars
```
But the infrastructure can be deployed using AWS CloudFormation (similar to ARM templates in Azure or GCP's CloudBuild) to set up the services like an RDS PostgreSQL database, the endpoint deployment, the S3 bucket, and the deployment of the Dagster image in a more AWS friendly way without having to use HCL or similar IaC coding like in Terraform, and you can also limit very well its capabilities to prevent issues, the learning curve is smoother for new members, here is the suggested architecture flow:

1. Git Push: A developer pushes changes to the CloudFormation templates (.yaml files) in a GitHub or AWS CodeCommit repository.
2. AWS CodePipeline Trigger: The push triggers the pipeline.
3. Source Stage: CodePipeline pulls the latest source code.
4. Build/Deploy Stage: CodePipeline invokes AWS CodeBuild.
5. CodeBuild Execution: CodeBuild runs commands defined in a buildspec.yml file. These commands instruct the AWS CLI to deploy the CloudFormation stacks.
6. CloudFormation Action: CloudFormation receives the template and provisions or updates the resources (RDS, S3, ECS Service for Dagster).

It would require this folder structure:

```
project-root/
├── cloudformation/
│   ├── 01-mlflow-backend-stack.yaml    # Template for S3 bucket, RDS, and Secrets Manager
│   ├── 02-dagster-ecs-stack.yaml       # Template for ECS Cluster, Task Definition, and Service
│   └── parameters/
│       ├── mlflow-dev-params.json      # Parameter values for the dev mlflow stack
│       ├── dagster-dev-params.json     # Parameter values for the dev dagster stack
│
├── dagster-app/                        # The Dagster orchestrator application code
│   └── Dockerfile                      # (This is already built and pushed to ECR)
│
└── buildspec.yml                       # Instructions for AWS CodeBuild
```

Here is a sample .yaml file for the MLFlow backend stack [resources provition](./../cloudformation/01-mlflow-backend-stack.yaml):


# Observability and Retraining

## How would you monitor for data drift or model degradation?

It is already explained in the previous steps that the batch prediction job would integrate the monitoring itself so it can be autoevaluated.

This process will consist of three key monitoring components:

- Model Degradation (Performance Monitoring): The primary method is tracking the model's predictive power on new, unseen data for which we have ground truth. As noted before, the core metric is the Concordance Index (C-index). For it a new Dagster asset will be created to join the predictions made in the past (3 months ago) with the newly available ground truth labels (i.e., which of those users actually churned). Another asset will then calculate the C-index for this recent cohort. This new C-index value will be logged back to the original MLflow run of the model version that made the predictions. This creates a time-series of performance metrics for each production model, allowing us to see exactly how its performance evolves over time.

- Data Drift (Input Monitoring): To monitor the statistical distribution of the key input features being fed into the model for prediction. This acts as an early warning system before model performance is affected.
Its implementation would be using a Dagster asset that uses a library like evidently.ai or scipy.stats (Kolmogorov-Smirnov test or similar). This asset will compare the statistical properties (mean, variance, distribution) of the incoming batch of data against a stable reference dataset (e.g., the original training data, which can be stored as an MLflow artifact). A drift score or a p-value for each feature will be calculated and logged as a metric to MLflow.

- Concept Drift (Output Monitoring): To monitor the distribution of the model's output scores. A sudden shift in the distribution of predicted churn risks can indicate that the underlying patterns of churn in the user base are changing. Its implementation is similar to data drift, a Dagster asset will compare the distribution of the latest prediction scores against the distribution of scores from a reference batch. A significant deviation, measured again by a statistical test, will be flagged and logged as a metric in MLflow.

## Where would you log metrics, alerts, and errors?

For the metrics, they can be stored in the MLFlow tracking service, storing all the metrics calculated by the Dagster monitoring assets named in the previous question to be logged here, tagged and run.

For visualization, Grafana is a good choice. A small scheduled job (maybe another Dagster asset) would periodically query the MLflow PostgreSQL backend and push the time series metrics into a time series scale database like Mimir, Prometheous or AWS Timestream and this will feed the Grafana dashboard.

For the alerts, Grafana has a tool specified for this called Grafana Alerting, using pseudo-sql statements like (`ALERT IF c_index < 0.75 FOR 1w or ALERT IF feature_ks_p_value < 0.01`). It can create notifications for Slack, email or similar channels. Some alerts has to be inside the pipeline run for immediate critical failure notification, for this the same Dagster job can include a Slack bot or similar approach.

The pipeline errors are already logged in the Dagster's UI, for traces, run metadata and similar for debugging failed prediction or monitoring jobs. For the infrastructure errors, it is possible to use the AWS logging services like AWS CloudWatch, it has aggregated data related to system level issues that might not be visible in Dagster logs. 

## What criteria would you use to trigger a retraining pipeline?

In the previous answers, something is already mentioned about this. As we are already monitoring the metrics, retraining can be triggered by a combination of reactive signals and proactive schedules. The goal is to act before business impact is felt. Any performance degradation like a C-index level drops under a predefined threshold for a sustained period (for xample two consecutive weekly measuerments), this would be reactive.

If any statistical or data drift is detected (failed Kolmogorov-Smirnov test, like a p value below 0.01) or the overall distribution of scores shift significantly, it should also indicate that a retraining is possible, and this can also be automated as mentioned before. 

Retraining should also be executed in mid term fixed time intervals (for example every 3 months) even if no significant metric calls the attention, to capture subtle and gradual changes in the user behavior before they cause impact. It also protects the deployment against not monitored spots or issues.

They could be scheduled and monitored by the Dagster assets but it is possible and recommended for example after a fixed term interval retraining, to add a Human in The Loop (HITL) sending a Slack message so the ML Team is aware that a new candidate model is ready for review before a model is in production replacing a well known performant version.