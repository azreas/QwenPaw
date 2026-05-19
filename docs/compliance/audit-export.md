# Audit Export

## Export JSON

```bash
curl -X POST http://127.0.0.1:8088/api/compliance/audit/export \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"format":"json","limit":1000}' \
  -o audit-export.json
```

## Export CSV

```bash
curl -X POST http://127.0.0.1:8088/api/compliance/audit/export \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"format":"csv","limit":1000}' \
  -o audit-export.csv
```

## Request Parameters

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| format | string | `json` | Export format: `json` or `csv` |
| limit | int | 1000 | Max rows (1-10000) |
| tenant_id | string | null | Filter by tenant |
| actor_id | string | null | Filter by actor |
| event_type | string | null | Filter by event type |
| start_time | datetime | null | Filter from time |
| end_time | datetime | null | Filter to time |

## Redaction

The exporter masks keys containing `token`, `secret`, `password`, `api_key`, or `cookie`.

## Retention Policy

```bash
curl http://127.0.0.1:8088/api/compliance/retention/policy \
  -H 'Authorization: Bearer <token>'
```

Returns default retention periods:

| Field | Default |
| --- | --- |
| audit_retention_days | 365 |
| backup_retention_days | 90 |
| spool_retention_days | 30 |
