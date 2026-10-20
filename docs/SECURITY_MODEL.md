# OS29 local developer / pentest security model

OS29 is designed for an operator-owned local lab. Its dev_pentest mode is not an unrestricted network or process mode: permission comes from exact configured scope and the currently logged-in Windows user.

## Hard boundaries

- HTTP gateway binds only to loopback and refuses startup if OS29_GATEWAY_TOKEN is absent or shorter than 32 characters.
- HTTP APIs other than minimal /health require bearer authentication. Token values are never printed and default HTTP access logging is disabled.
- MCP stdio is a narrow local tool surface; it exposes observation, evidence, capsule, capability and candidate-lesson operations, not arbitrary shell execution, raw file writes or a generic Frida attach method.
- The MITM addon only persists requests to explicitly scoped targets and ports. Out-of-scope requests are not persisted by the addon; this is not a network firewall.
- Frida requires an exact device ID, existing PID, class/method, and executable process name allowlisted in config/lab_scope.json. Both approved_device_ids and approved_process_names start empty. No automatic app spawn, patching or certificate-pinning bypass is performed.
- HTTP bodies and raw header values are off by default. Frida argument values, return values and full exception messages are not recorded.
- Sensitive keys, bearer-like strings, JWT-like strings and private-key blocks are redacted before database persistence.
- Mission capsules, incident hypotheses and experience candidates preserve evidence source IDs. Correlation is not treated as proof of root cause.
- Experience is not auto-promoted from candidate to validated; the MCP API intentionally has no validation operation. The separate local CLI validation action requires reviewing the linked event and an exact human-typed confirmation.
- The stdio server runs as the Windows user launching it; the advertised tool allowlist is not a kernel sandbox against arbitrary other code running as that user.

## Scope changes

Default approved hosts are 127.0.0.1, localhost and ::1. Default ports are 8766, 8771 and 8772. Approved networks are loopback only. Frida's approved device-ID and process-name lists start empty.

To broaden scope, edit config/lab_scope.json deliberately and record who approved the target, reason, time window and data-retention requirements. Avoid wildcard hostnames and broad LAN CIDRs unless the engagement explicitly requires them. The Frida bridge fails closed when the device ID or process name does not match the configured lists.

## Limits and assumptions

- The local store is SQLite, not encrypted at rest. Avoid unnecessary sensitive payloads.
- Redaction is defensive, not a guarantee that every proprietary or personally identifying field can be recognized. The build limits captured fields and omits request/response bodies.
- The tested MITM flow was one benign health request to 127.0.0.1:8766. Frida enumeration found no connected Android test device; no app attachment was attempted.
