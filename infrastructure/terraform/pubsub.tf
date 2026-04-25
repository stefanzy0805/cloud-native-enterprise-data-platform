# -------------------------------------------------------
# Pub/Sub: Real-time event streaming
# -------------------------------------------------------

resource "google_pubsub_topic" "github_events_raw" {
  name = "github-events-raw"

  message_retention_duration = "86600s"  # 24h

  labels = { layer = "raw", source = "github-api" }
}

resource "google_pubsub_topic" "github_events_dlq" {
  name   = "github-events-raw-dlq"
  labels = { type = "dead-letter" }
}

resource "google_pubsub_subscription" "github_events_bq_sub" {
  name  = "github-events-bq-writer"
  topic = google_pubsub_topic.github_events_raw.name

  ack_deadline_seconds       = 60
  message_retention_duration = "3600s"  # 1h unacked retention

  # Auto-retry with exponential backoff
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Dead letter after 5 failed deliveries
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.github_events_dlq.id
    max_delivery_attempts = 5
  }

  labels = { consumer = "bq-writer" }
}

# -------------------------------------------------------
# Pub/Sub: Pipeline status events (for monitoring)
# -------------------------------------------------------
resource "google_pubsub_topic" "pipeline_status" {
  name   = "pipeline-status"
  labels = { purpose = "monitoring" }
}

# -------------------------------------------------------
# IAM
# -------------------------------------------------------
resource "google_pubsub_topic_iam_member" "ingest_publish_raw" {
  topic  = google_pubsub_topic.github_events_raw.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.svc_ingest.email}"
}

resource "google_pubsub_subscription_iam_member" "etl_subscribe_raw" {
  subscription = google_pubsub_subscription.github_events_bq_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.svc_etl.email}"
}
