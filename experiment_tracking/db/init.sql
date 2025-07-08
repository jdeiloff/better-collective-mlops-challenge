-- SQL commands to create the MLflow schema in PostgreSQL

CREATE TABLE experiments (
    experiment_id integer NOT NULL,
    name character varying(256) NOT NULL,
    artifact_location character varying(256),
    lifecycle_stage character varying(32),
    CONSTRAINT experiments_pkey PRIMARY KEY (experiment_id),
    CONSTRAINT experiments_name_key UNIQUE (name)
);

CREATE TABLE runs (
    run_uuid character varying(32) NOT NULL,
    name character varying(250),
    source_type character varying(20),
    source_name character varying(500),
    entry_point_name character varying(50),
    user_id character varying(256),
    status character varying(9),
    start_time bigint,
    end_time bigint,
    source_version character varying(50),
    lifecycle_stage character varying(20),
    artifact_uri character varying(200),
    experiment_id integer,
    CONSTRAINT runs_pkey PRIMARY KEY (run_uuid),
    CONSTRAINT runs_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

CREATE TABLE metrics (
    key character varying(250) NOT NULL,
    value double precision NOT NULL,
    "timestamp" bigint NOT NULL,
    run_uuid character varying(32) NOT NULL,
    step bigint DEFAULT 0 NOT NULL,
    is_nan boolean DEFAULT false NOT NULL,
    CONSTRAINT metrics_pkey PRIMARY KEY (run_uuid, key, "timestamp", step),
    CONSTRAINT metrics_run_uuid_fkey FOREIGN KEY (run_uuid) REFERENCES runs(run_uuid)
);

CREATE TABLE params (
    key character varying(250) NOT NULL,
    value character varying(250) NOT NULL,
    run_uuid character varying(32) NOT NULL,
    CONSTRAINT params_pkey PRIMARY KEY (run_uuid, key),
    CONSTRAINT params_run_uuid_fkey FOREIGN KEY (run_uuid) REFERENCES runs(run_uuid)
);

CREATE TABLE tags (
    key character varying(250) NOT NULL,
    value character varying(5000),
    run_uuid character varying(32) NOT NULL,
    CONSTRAINT tags_pkey PRIMARY KEY (run_uuid, key),
    CONSTRAINT tags_run_uuid_fkey FOREIGN KEY (run_uuid) REFERENCES runs(run_uuid)
);

CREATE TABLE artifacts (
    run_uuid character varying(32) NOT NULL,
    path character varying(256) NOT NULL,
    is_dir boolean,
    file_size bigint,
    CONSTRAINT artifacts_pkey PRIMARY KEY (run_uuid, path),
    CONSTRAINT artifacts_run_uuid_fkey FOREIGN KEY (run_uuid) REFERENCES runs(run_uuid)
);
