# -------------------------------------------------------
# BigQuery Tables: raw layer
# -------------------------------------------------------

resource "google_bigquery_table" "raw_github_events" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "github_events"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "_ingested_at"
  }

  # Schema mirrors GitHub Events API response
  schema = jsonencode([
    { name = "id",           type = "STRING",    mode = "NULLABLE" },
    { name = "type",         type = "STRING",    mode = "NULLABLE" },
    { name = "actor",        type = "JSON",      mode = "NULLABLE" },
    { name = "repo",         type = "JSON",      mode = "NULLABLE" },
    { name = "payload",      type = "JSON",      mode = "NULLABLE" },
    { name = "public",       type = "BOOLEAN",   mode = "NULLABLE" },
    { name = "created_at",   type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "_ingested_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "_run_id",      type = "STRING",    mode = "NULLABLE" },
    { name = "_source",      type = "STRING",    mode = "NULLABLE" },
  ])

  labels = { layer = "raw", domain = "github" }
}

# -------------------------------------------------------
# BigQuery Tables: staging layer
# -------------------------------------------------------

resource "google_bigquery_table" "staging_github_events" {
  dataset_id          = google_bigquery_dataset.staging.dataset_id
  table_id            = "github_events"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "event_date"
  }

  clustering = ["event_type", "repo_name"]

  schema = jsonencode([
    { name = "event_id",     type = "STRING",    mode = "REQUIRED" },
    { name = "event_type",   type = "STRING",    mode = "NULLABLE" },
    { name = "event_date",   type = "DATE",      mode = "NULLABLE" },
    { name = "event_ts",     type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "actor_login",  type = "STRING",    mode = "NULLABLE" },
    { name = "repo_name",    type = "STRING",    mode = "NULLABLE" },
    { name = "is_public",    type = "BOOLEAN",   mode = "NULLABLE" },
    { name = "_ingested_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "_processed_at",type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  labels = { layer = "staging", domain = "github" }
}

# -------------------------------------------------------
# BigQuery Tables: serving layer
# -------------------------------------------------------

resource "google_bigquery_table" "serving_daily_event_stats" {
  dataset_id          = google_bigquery_dataset.serving.dataset_id
  table_id            = "daily_event_stats"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "event_date"
  }

  clustering = ["event_type"]

  schema = jsonencode([
    { name = "event_date",   type = "DATE",    mode = "REQUIRED" },
    { name = "event_type",   type = "STRING",  mode = "REQUIRED" },
    { name = "event_count",  type = "INTEGER", mode = "NULLABLE" },
    { name = "unique_actors",type = "INTEGER", mode = "NULLABLE" },
    { name = "unique_repos", type = "INTEGER", mode = "NULLABLE" },
    { name = "_updated_at",  type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  labels = { layer = "serving", domain = "github" }
}

resource "google_bigquery_table" "serving_top_repos" {
  dataset_id          = google_bigquery_dataset.serving.dataset_id
  table_id            = "top_repos_daily"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "event_date"
  }

  schema = jsonencode([
    { name = "event_date",    type = "DATE",    mode = "REQUIRED" },
    { name = "repo_name",     type = "STRING",  mode = "REQUIRED" },
    { name = "event_count",   type = "INTEGER", mode = "NULLABLE" },
    { name = "unique_actors", type = "INTEGER", mode = "NULLABLE" },
    { name = "event_types",   type = "STRING",  mode = "NULLABLE" },
    { name = "_updated_at",   type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  labels = { layer = "serving", domain = "github" }
}
