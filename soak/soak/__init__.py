"""ge-soak: 24-hour reliability and usage soak test for the Gemini Enterprise
Stream Assist API. Runs as a Cloud Run Job on a Cloud Scheduler cadence,
writes one JSON record per run to GCS, and renders a report artifact."""

__version__ = "0.1.0"
