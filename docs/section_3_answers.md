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


