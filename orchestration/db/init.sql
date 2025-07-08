CREATE TABLE IF NOT EXISTS churn_predictions (
    id SERIAL PRIMARY KEY,
    prediction_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    geography_id VARCHAR(255), -- Asuming the multiple geographies approach
    churn_probability FLOAT,
    model_version VARCHAR(50)
);
