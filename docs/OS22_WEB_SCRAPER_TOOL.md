# OS-22 Web Scraper Tool

## Purpose

`web_scrape` is the OS-22 Web Learning fetch tool.

It fetches only `http` and `https` URLs, extracts clean text from HTML, and
returns bounded JSON metadata for RAG ingestion.

## Tool Contract

```text
TOOL_CALL: web_scrape {"url": "https://example.com", "max_chars": 8000}
```

Arguments:

- `url`: required `http` or `https` URL
- `max_chars`: optional text limit, default `8000`
- `timeout`: optional network timeout, default `30`

Output schema:

```text
ana.os22.web_scrape.v1
```

## Safety

- rejects non-http schemes
- does not write files
- does not store memory by itself
- returns ASCII-safe text
- keeps output bounded by `max_chars`

## Files

```text
ANA_MAX/tools/web_scraper.py
ANA_MAX/local/tool_dispatcher.py
ANA_MAX/tools/tool_manifest.json
```
