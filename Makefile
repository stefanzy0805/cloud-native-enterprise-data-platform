PROJECT_ID  ?= gcp-lab-data-engineering
REGION      ?= us-central1
DATE        ?= $(shell date +%Y-%m-%d)
RAW_BUCKET  := $(PROJECT_ID)-datalake-raw

.PHONY: help setup install tf-init tf-plan tf-apply ingest load transform dq run test

help:
	@echo ""
	@echo "Usage: make <target> [DATE=YYYY-MM-DD] [PROJECT_ID=your-project]"
	@echo ""
	@echo "Setup:"
	@echo "  setup       Enable GCP APIs and configure gcloud"
	@echo "  install     Install Python dependencies"
	@echo "  tf-init     Terraform init"
	@echo "  tf-plan     Terraform plan (review changes)"
	@echo "  tf-apply    Terraform apply (provision infra)"
	@echo ""
	@echo "Pipeline (run daily, in order):"
	@echo "  ingest      Fetch GitHub Events → GCS raw"
	@echo "  dq-raw      Data quality checks on raw layer"
	@echo "  load        GCS → BigQuery raw table"
	@echo "  transform   raw → staging → serving (BigQuery SQL)"
	@echo "  dq-staging  Data quality checks on staging layer"
	@echo "  dq-serving  Data quality checks on serving layer"
	@echo "  run         Full pipeline (all steps above)"
	@echo ""
	@echo "Dev:"
	@echo "  test        Run unit tests"
	@echo "  ingest-local Ingest to local filesystem (no GCP needed)"
	@echo ""

# -------------------------------------------------------
# Setup
# -------------------------------------------------------
setup:
	gcloud config set project $(PROJECT_ID)
	gcloud services enable \
		storage.googleapis.com \
		bigquery.googleapis.com \
		pubsub.googleapis.com \
		secretmanager.googleapis.com \
		cloudscheduler.googleapis.com \
		run.googleapis.com \
		--project $(PROJECT_ID)
	@echo "APIs enabled."

install:
	pip install -r requirements.txt -r requirements-dev.txt

# -------------------------------------------------------
# Terraform
# -------------------------------------------------------
tf-init:
	cd infrastructure/terraform && terraform init

tf-plan:
	cd infrastructure/terraform && terraform plan -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)"

tf-apply:
	cd infrastructure/terraform && terraform apply -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)" -auto-approve

# -------------------------------------------------------
# Pipeline steps
# -------------------------------------------------------
ingest:
	python -m ingestion.api_ingest --date $(DATE) --sink gcs

ingest-local:
	python -m ingestion.api_ingest --date $(DATE) --sink local --limit 50

dq-raw:
	python -m data_quality.checks --date $(DATE) --layer raw --project $(PROJECT_ID)

load:
	python -m etl.load --date $(DATE) --project $(PROJECT_ID)

transform:
	python -m etl.transform --date $(DATE) --project $(PROJECT_ID)

dq-staging:
	python -m data_quality.checks --date $(DATE) --layer staging --project $(PROJECT_ID)

dq-serving:
	python -m data_quality.checks --date $(DATE) --layer serving --project $(PROJECT_ID)

run:
	python -m orchestration.pipeline --date $(DATE) --project $(PROJECT_ID)

run-dry:
	python -m orchestration.pipeline --date $(DATE) --project $(PROJECT_ID) --dry-run

# -------------------------------------------------------
# Testing
# -------------------------------------------------------
test:
	python -m pytest tests/ -v --tb=short

test-cov:
	python -m pytest tests/ -v --cov=ingestion --cov=etl --cov=data_quality --cov=orchestration --cov-report=term-missing
