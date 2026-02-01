-- Initialize database schemas for data platform
-- This script runs automatically when the postgres container starts for the first time

-- Create schemas for different data layers
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS serving;
CREATE SCHEMA IF NOT EXISTS metadata;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA raw TO dataplatform;
GRANT ALL PRIVILEGES ON SCHEMA staging TO dataplatform;
GRANT ALL PRIVILEGES ON SCHEMA serving TO dataplatform;
GRANT ALL PRIVILEGES ON SCHEMA metadata TO dataplatform;

-- Create a simple metadata table for tracking ingestion jobs
CREATE TABLE IF NOT EXISTS metadata.ingestion_log (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    ingestion_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    records_count INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    metadata JSONB
);

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_ingestion_log_source
    ON metadata.ingestion_log(source_name, ingestion_time DESC);

COMMENT ON SCHEMA raw IS 'Raw data layer - append-only, unprocessed data';
COMMENT ON SCHEMA staging IS 'Staging layer - cleaned and validated data';
COMMENT ON SCHEMA serving IS 'Serving layer - business-ready, aggregated data';
COMMENT ON SCHEMA metadata IS 'Metadata and logging tables';
