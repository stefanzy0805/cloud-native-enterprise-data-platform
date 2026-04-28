# credentials

This directory is for local credential files only.

Place sensitive files here, for example:

```text
credentials/
  gcp-service-account.json
```

The project `.env` points to the GCP service account file with:

```env
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-service-account.json
```

Do not commit real credential files. Only this README should be tracked.
