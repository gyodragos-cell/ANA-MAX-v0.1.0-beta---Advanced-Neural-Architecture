# Tool Testing

Use `test_all_tools.py` to run a safe end-to-end smoke test through
`ana-max-bridge`.

The tester:

- calls `GET /tools/list`;
- generates safe `params` for known tools;
- calls `POST /tools/call`;
- records HTTP status, timing, response shape, and errors;
- skips risky, premium, destructive, screen-capture, and external-network
  tools by default.

Run from the repository root:

```powershell
python ana-max-bridge\test_all_tools.py
```

Reports are written outside the repository by default:

```text
%TEMP%\ana-max-tool-test
```

The tester refuses non-local bridge URLs. It is intended for LOCAL DEV MODE on
`127.0.0.1`.

To test a larger private ANA MAX workspace, copy the same script into that
workspace and run it against that workspace's bridge. Do not copy private
reports back into this public release.
