# OS-22 Web Learning Pipeline

## Purpose

Web Learning lets the local agent learn bounded text from a user-approved URL
and store it in local semantic memory.

The pipeline is explicit and tool-driven.

## Pipeline

```text
User asks to learn from URL
  -> TOOL_CALL: web_scrape {"url": "...", "max_chars": 8000}
  -> tool returns clean text
  -> TOOL_CALL: rag_store_text {"text": "...", "source": "..."}
  -> RAGBridge stores chunks in VectorMemoryCortex
  -> agent confirms short result
```

## Tools

### web_scrape

Fetches HTML and returns clean text.

### rag_store_text

Stores text chunks into RAGBridge with source metadata.

Contract:

```text
TOOL_CALL: rag_store_text {"text": "...", "source": "https://example.com"}
```

Optional arguments:

- `chunk_size`
- `chunk_overlap`

Output schema:

```text
ana.os22.rag_store_text.v1
```

## Rules

- one tool call per turn
- no automatic browsing without user intent
- no non-http URLs for web scraping
- no memory write until `rag_store_text` is called
- store stable useful text only

## Validation

Relevant tests:

```text
tests/test_os22_web_learning_tools.py
tests/test_tool_manifest_loader.py
tests/test_tool_dispatcher.py
```
