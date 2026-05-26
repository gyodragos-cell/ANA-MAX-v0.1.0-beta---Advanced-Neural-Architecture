# ANA MAX Security And Privacy

## Data Boundaries

Keep private memory, logs, screenshots, local configs, and secrets in dev/lab
workspaces only.

## Logging Rules

Audit logs record metadata and outcomes. They must redact token, secret,
password, and API key fields.

## Redaction

Redaction is required before public export or dashboard display.

## Lab-Only vs Public

Lab-only: memory stores, optimization snapshots, session archives, local
endpoints, private datasets.

Public-safe: architecture docs, policy descriptions, test matrices, high-level
roadmaps.
