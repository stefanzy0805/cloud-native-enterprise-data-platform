# ------------------------
# Service Accounts
# ------------------------

resource "google_service_account" "svc_ingest" {
  account_id   = "svc-ingest"
  display_name = "Ingestion Service Account"
}

resource "google_service_account" "svc_etl" {
  account_id   = "svc-etl"
  display_name = "ETL Service Account"
}

resource "google_service_account" "svc_analytics" {
  account_id   = "svc-analytics"
  display_name = "Analytics Service Account"
}


# ETL read raw
resource "google_bigquery_dataset_iam_member" "etl_read_raw" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.svc_etl.email}"
}

# ETL write staging
resource "google_bigquery_dataset_iam_member" "etl_write_staging" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.svc_etl.email}"
}

# ETL write serving
resource "google_bigquery_dataset_iam_member" "etl_write_serving" {
  dataset_id = google_bigquery_dataset.serving.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.svc_etl.email}"
}



resource "google_bigquery_dataset_iam_member" "analytics_read_serving" {
  dataset_id = google_bigquery_dataset.serving.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.svc_analytics.email}"
}
