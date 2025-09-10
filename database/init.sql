-- init_all.sql
-- Initialize SQLite schema for PodML MVP
-- Run with:  sqlite3 app.db < init_all.sql

PRAGMA foreign_keys = ON;

------------------------------------------------------------
-- Configurations
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configurations (
    id TEXT PRIMARY KEY,                  -- UUID as string
    owner_sub TEXT NOT NULL,              -- Cognito user sub
    name TEXT NOT NULL,                   -- Human-readable name
    dataset_uri TEXT NOT NULL,            -- Path or URI to dataset
    x_column TEXT NOT NULL,               -- Independent variable column name
    y_column TEXT NOT NULL,               -- Dependent variable column name
    model_type TEXT NOT NULL DEFAULT 'linear_regression',
    hyperparams_json TEXT,                -- JSON blob (stringified)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_configurations_owner
    ON configurations (owner_sub, created_at DESC);

------------------------------------------------------------
-- Training Jobs
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_jobs (
  id TEXT PRIMARY KEY,                      -- UUID as string
  owner_sub TEXT NOT NULL,
  configuration_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',    -- queued|running|succeeded|failed
  k8s_job_name TEXT NOT NULL,
  model_uri TEXT,                           -- file:// or s3://
  metrics_json TEXT,                        -- JSON text (r2, mse, etc.)
  resources_json TEXT,                      -- JSON text for req/limits used
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_training_jobs_owner
    ON training_jobs (owner_sub, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_training_jobs_cfg
    ON training_jobs (configuration_id, created_at DESC);

-- (Optional) seed example
-- INSERT INTO configurations (id, owner_sub, name, dataset_uri, x_column, y_column, model_type)
-- VALUES ('11111111-1111-1111-1111-111111111111', 'sub-1234', 'Demo Config',
--         '/Users/you/data/demo.csv', 'feature', 'target', 'linear_regression');
