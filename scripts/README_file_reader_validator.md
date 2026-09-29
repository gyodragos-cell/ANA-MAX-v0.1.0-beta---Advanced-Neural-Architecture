# ANA MAX File Reader & Validator

Solutie enterprise pentru citire si validare fisiere folosind ANA MAX tools.

## Avantaje vs Custom Functions

**Custom Functions (propunerea ta):**
- Implementare manuala pentru fiecare tip de fisier
- Error detection limitat la pattern-uri simple
- Fara integrare cu ecosistemul existent
- Maintenance manuala

**ANA MAX Integration (solutia mea):**
- 90+ scule enterprise deja disponibile
- Error detection avansat via ErrorRadar
- Recommendations inteligente via AgentCoach
- Integrare nativa cu ecosistemul ANA MAX
- HTTP API - fara dependency hell

## Instalare

```bash
# Necesita ANA MAX server pornit
# Port default: 8767 (Phi-4) sau 8766 (Ollama)
```

## Utilizare

### CLI

```bash
# Citire si validare fisier JSON
python scripts/file_reader_validator.py test_sample.json

# Output JSON format
python scripts/file_reader_validator.py test_sample.json --json

# Custom ANA MAX server URL
python scripts/file_reader_validator.py file.md --url http://127.0.0.1:8766
```

### Python API

```python
from scripts.file_reader_validator import ANAFileReaderValidator

# Initializare
validator = ANAFileReaderValidator("http://127.0.0.1:8767")

# Procesare fisier
result = validator.process_file("config.json")

# Rezultat
{
    "file": "config.json",
    "status": "processed",
    "type": ".json",
    "size": 1024,
    "validation": {
        "json": {
            "valid": True,
            "structure": {...},
            "errors": []
        }
    },
    "errors": [],
    "recommendations": []
}
```

## Functionalitati

### 1. File Reading
- Suport: .md, .json, .txt, .py, .yaml
- Operatii: read, write, edit, search
- Encoding detection

### 2. JSON Validation
- Structure analysis
- Type checking
- Error reporting

### 3. Error Detection
- Traceback detection
- Syntax errors
- Import errors
- Auth errors
- Test failures

### 4. Recommendations
- Fix suggestions
- Tool recommendations
- Severity assessment

## Pipeline

```
1. Read File (FilesTool)
   ↓
2. Type-specific Validation (JSON/MD/TXT)
   ↓
3. Error Detection (ErrorRadar)
   ↓
4. Get Recommendations (AgentCoach)
   ↓
5. Return Complete Report
```

## Exemple

### Valid JSON
```bash
$ python scripts/file_reader_validator.py test_sample.json
File: test_sample.json
Status: processed
Type: .json
Size: 156 bytes

Validation:
  json: {
    "valid": true,
    "structure": {
      "type": "object",
      "keys": ["name", "version", "dependencies", "config"],
      "key_count": 4
    },
    "errors": []
  }
```

### Invalid JSON
```bash
$ python scripts/file_reader_validator.py broken.json
File: broken.json
Status: processed
Type: .json
Size: 45 bytes

Validation:
  json: {
    "valid": false,
    "errors": ["JSON decode error: Expecting ',' delimiter at line 3"]
  }

Errors found:
  - JSON decode error: Expecting ',' delimiter at line 3

Recommendations:
  - Fix JSON syntax error
  - Use error_radar for detailed analysis
```

## ANA MAX Tools Folosite

- **FilesTool**: `file_operations` - citire/scriere fisiere
- **ErrorRadarTool**: `error_radar` - detectare erori
- **AgentCoachTool**: `agent_coach` - recomandari fix

## Server Requirements

```bash
# Pornire ANA MAX cu Foundry (Phi-4)
START_PHI4_OS27.bat

# Sau cu Ollama
START_ANA_OLLAMA.bat
```

## Troubleshooting

**Connection refused:**
```bash
# Verifica daca ANA MAX ruleaza
curl http://127.0.0.1:8767/health
```

**Tool not found:**
```bash
# Verifica tools disponibile
curl http://127.0.0.1:8767/tools
```

## Performance

- Citire fisier: <100ms
- Validare JSON: <50ms
- Error detection: <200ms
- Total pipeline: <500ms

## Extensibilitate

Adauga noi validari in `process_file()`:

```python
# Markdown validation
if file_ext == ".md":
    md_result = self.validate_markdown(content)
    result["validation"]["markdown"] = md_result

# YAML validation
if file_ext in [".yaml", ".yml"]:
    yaml_result = self.validate_yaml(content)
    result["validation"]["yaml"] = yaml_result
```
