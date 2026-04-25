# -------------------------------------------------------
# GCS Data Lake Buckets (Medallion: raw / staging / serving)
# -------------------------------------------------------

locals {
  bucket_prefix = var.project_id
}

resource "google_storage_bucket" "raw" {
  name                        = "${local.bucket_prefix}-datalake-raw"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition { age = 90 }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition { age = 365 }
  }

  labels = { layer = "raw", team = "data-engineering" }
}

resource "google_storage_bucket" "staging" {
  name                        = "${local.bucket_prefix}-datalake-staging"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 730 }  # 2 years
  }

  labels = { layer = "staging", team = "data-engineering" }
}

resource "google_storage_bucket" "temp" {
  name                        = "${local.bucket_prefix}-pipeline-temp"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 7 }  # clean up temp files after 7 days
  }

  labels = { layer = "temp", team = "data-engineering" }
}

# -------------------------------------------------------
# IAM: Ingestion SA → write raw bucket
# -------------------------------------------------------
resource "google_storage_bucket_iam_member" "ingest_write_raw" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.svc_ingest.email}"
}

resource "google_storage_bucket_iam_member" "etl_read_raw_gcs" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.svc_etl.email}"
}

resource "google_storage_bucket_iam_member" "etl_write_staging_gcs" {
  bucket = google_storage_bucket.staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.svc_etl.email}"
}

resource "google_storage_bucket_iam_member" "etl_write_temp" {
  bucket = google_storage_bucket.temp.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.svc_etl.email}"
}
