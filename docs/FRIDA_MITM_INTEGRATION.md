# Optional Frida and MITM integrations

These adapters are optional lab sensors. They are not started automatically by the OS29 CLI or MCP server, and they are not a network firewall or a certified security product.

## Default scope

- HTTP(S) targets must match the exact configured allowlist; local defaults are loopback only.
- Frida attachment requires both an approved device ID and the exact approved process executable name. Both lists start empty.
- Request/response bodies, raw header values, Frida arguments and return values are not stored by default.
- Use only devices, processes and targets that you own or are explicitly authorized to test.
- Keep proxy/browser profiles, flow captures, screenshots, logs and SQLite stores outside the public repository.

## Acceptance boundary

The recorded local smoke used one benign loopback health request and stored metadata-only events. No real Android/USB target was available in that checkpoint; no live app attach, certificate-pinning bypass or end-to-end application fix/retest is claimed.

For sustained proxy work, use a dedicated environment with the optional tool installed, explicit scope approval, bounded retention and a review of captured data. Do not broaden CIDRs or add a process to the Frida allowlist by default.
