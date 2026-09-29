# ANA MAX OS v2 Skills Reference

## Overview

Skills are declarative, high-level capabilities that define how ANA MAX OS v2 should perform specific tasks. Unlike tools (which are low-level functions), skills provide structured guidance for complex operations.

## Skill Structure

Every skill must have the following sections:

### Required Sections

1. **Context**: Background and purpose of the skill
2. **Scop**: Scope and objectives
3. **Structura directoare**: Directory structure involved
4. **Componente OS v2**: OS v2 components used
5. **Discipline OS v2**: OS v2 disciplines enforced
6. **Taskuri pentru implementare**: Implementation tasks
7. **Reguli pentru Codex**: Rules for Codex (the AI agent)
8. **Output asteptat**: Expected output format

### Optional Sections

- **Version**: Skill version (required for declarative skills)
- **Fallback conditions**: When to use fallback
- **Dependencies**: Other skills or tools required

## Available Skills

### self-repair

**Location:** `ana/skills/skills/self-repair/SKILL.md`

**Version:** 1.0.0

**Capability:** `self.repair`

**Purpose:** Self-repair and system recovery

**Description:**
The self-repair skill enables ANA MAX OS v2 to diagnose and fix issues automatically. It includes:
- Error analysis and diagnosis
- Patch generation and application
- Rollback capabilities
- Health monitoring

**Key Tasks:**
- Analyze error patterns
- Generate repair patches
- Apply patches safely
- Verify repairs
- Rollback if needed

**Fallback Conditions:**
- Multiple consecutive failures
- Unknown error types
- System instability

**Output Format:**
```json
{
  "status": "success|failed",
  "patches_applied": 0,
  "patches_failed": 0,
  "rollback_performed": false,
  "details": {}
}
```

### health-check

**Location:** `ana/skills/skills/health-check/SKILL.md`

**Version:** 1.0.0

**Capability:** `health.check`

**Purpose:** System health monitoring

**Description:**
The health-check skill monitors the health of ANA MAX OS v2 components:
- Event bus health
- Tool registry status
- Sandbox status
- LLM service connectivity
- Memory usage
- Performance metrics

**Key Tasks:**
- Check component status
- Monitor resource usage
- Detect anomalies
- Generate health reports
- Alert on issues

**Output Format:**
```json
{
  "overall_status": "healthy|degraded|unhealthy",
  "components": {
    "event_bus": "healthy",
    "tool_registry": "healthy",
    "sandbox": "healthy",
    "llm_service": "healthy"
  },
  "metrics": {
    "memory_usage_mb": 0,
    "cpu_usage_percent": 0,
    "event_queue_size": 0
  },
  "alerts": []
}
```

### fs-inspect

**Location:** `ana/skills/skills/fs-inspect/SKILL.md`

**Version:** 1.0.0

**Capability:** `fs.inspect`

**Purpose:** File system inspection and analysis

**Description:**
The fs-inspect skill provides comprehensive file system analysis:
- Directory structure analysis
- File type detection
- Size analysis
- Permission analysis
- Dependency mapping
- Code structure analysis

**Key Tasks:**
- Scan directory structure
- Analyze file types
- Map dependencies
- Detect patterns
- Generate reports

**Output Format:**
```json
{
  "path": "/path/to/directory",
  "file_count": 0,
  "directory_count": 0,
  "total_size_bytes": 0,
  "file_types": {},
  "structure": {},
  "dependencies": []
}
```

## Skill Configuration

Skills are configured in `ana/config/skills.yaml`:

```yaml
skills:
  self.repair:
    skill: self-repair
    capability: self.repair
    version: 1.0.0
    enabled: true

  health.check:
    skill: health-check
    capability: health.check
    version: 1.0.0
    enabled: true

  fs.inspect:
    skill: fs-inspect
    capability: fs.inspect
    version: 1.0.0
    enabled: true
```

## Skill Execution

### Using the Unified System

```python
from ana_unified import UnifiedANASystem

system = UnifiedANASystem()

# Execute a skill
response = system.execute_capability(
    "health.check",
    {},
    trace_id="health-check-trace"
)
```

### Using OS v2 Directly

```python
from ana.core.orchestrator.orchestrator import ANAMaxOS
from ana.config.loader import ConfigLoader
from ana.tools.registry.registry import ToolRegistry

config = ConfigLoader().load("ana/config/defaults.yaml")
registry = ToolRegistry()

os_runtime = ANAMaxOS(config=config, registry=registry)

# Execute a skill
response = os_runtime.execute(
    "health.check",
    {},
    trace_id="health-check-trace"
)
```

## Creating New Skills

### Step 1: Create Skill Directory

```bash
mkdir -p ana/skills/skills/my-skill
```

### Step 2: Create SKILL.md

```markdown
# Skill: my-skill

## Version
1.0.0

## Context
Description of the skill's purpose and context...

## Scop
Scope and objectives of the skill...

## Structura directoare
Directory structure involved...

## Componente OS v2
1. Component one
2. Component two

## Discipline OS v2
- Determinism
- Observability
- Fail fast

## Taskuri pentru implementare
### A. Task one
Description...

### B. Task two
Description...

## Reguli pentru Codex
- Rule one
- Rule two

## Output asteptat
```json
{
  "status": "success",
  "result": "..."
}
```
```

### Step 3: Register Skill

Add to `ana/config/skills.yaml`:

```yaml
skills:
  my.skill:
    skill: my-skill
    capability: my.skill
    version: 1.0.0
    enabled: true
```

### Step 4: Test Skill

```bash
python ana_unified.py --list-capabilities
```

## Skill Validation

The skill engine validates skills against the following rules:

### Required Sections

All skills must have:
- Context
- Scop
- Structura directoare
- Componente OS v2
- Discipline OS v2
- Taskuri pentru implementare
- Reguli pentru Codex
- Output asteptat

### Version Requirement

Declarative skills (in `ana/skills/skills/`) must have a version.

### Heading Normalization

Headings are normalized to ASCII for comparison:
- Romanian diacritics converted (aa, ss, tt, etc.)
- Numbered prefixes removed (1. Context  Context)
- Parenthetical content removed (Context (obligatoriu)  Context)

## Skill Engine

**Location:** `ana/tools/registry/skill_engine.py`

**Key Features:**
- Heading normalization with caching
- Required section validation
- Version enforcement
- Diacritic normalization
- Skill registration

**Performance Optimizations:**
- Heading normalization cache
- Efficient section validation
- Lazy skill loading

## Skill vs Tools

### Skills
- High-level, declarative
- Structured guidance
- Complex operations
- Multiple steps
- Context-aware

### Tools
- Low-level, imperative
- Single operations
- Simple functions
- Immediate execution
- Stateless

## Skill Composition

Skills can be composed of multiple tools:

```yaml
skills:
  complex.operation:
    skill: complex-operation
    capability: complex.operation
    version: 1.0.0
    enabled: true
    tools:
      - tool1
      - tool2
      - tool3
```

## Skill Fallback

Skills can define fallback conditions:

```markdown
## Fallback conditions
- If primary tool fails 3 times
- If timeout exceeds 30 seconds
- If error is non-recoverable
```

## Skill Testing

### Unit Tests

```python
def test_skill_parsing():
    engine = SkillEngine()
    skill_text = """
    # Skill: test
    ## Context
    Test context...
    """
    spec = engine.parse(skill_text)
    assert spec.title == "test"
```

### Integration Tests

```python
def test_skill_execution():
    system = UnifiedANASystem()
    response = system.execute_capability("health.check", {})
    assert response.status == "success"
```

## Skill Best Practices

1. **Clear Purpose**: Define the skill's purpose clearly in Context
2. **Scoped Objectives**: Keep scope focused and achievable
3. **Component Mapping**: List all OS v2 components used
4. **Discipline Enforcement**: Specify OS v2 disciplines
5. **Task Breakdown**: Break implementation into clear tasks
6. **Codex Rules**: Provide clear rules for the AI agent
7. **Structured Output**: Define expected output format
8. **Version Management**: Use semantic versioning
9. **Documentation**: Keep SKILL.md up to date
10. **Testing**: Add tests for each skill

## Skill Examples

### Example: Code Analysis Skill

```markdown
# Skill: code-analysis

## Version
1.0.0

## Context
Analyze codebase for quality, security, and performance issues.

## Scop
Identify code smells, security vulnerabilities, and performance bottlenecks.

## Structura directoare
- Project root
- Source directories
- Test directories

## Componente OS v2
1. Tool Registry
2. Orchestrator
3. Event Bus

## Discipline OS v2
- Determinism
- Observability
- Security

## Taskuri pentru implementare
### A. Scan codebase
Scan all source files for patterns.

### B. Analyze quality
Check code quality metrics.

### C. Check security
Identify security vulnerabilities.

### D. Check performance
Find performance bottlenecks.

## Reguli pentru Codex
- Use static analysis tools
- Check for common vulnerabilities
- Analyze complexity
- Review dependencies

## Output asteptat
```json
{
  "status": "success",
  "issues": {
    "quality": [],
    "security": [],
    "performance": []
  },
  "summary": {}
}
```
```

## Skill Troubleshooting

### Skill Not Found

**Problem:** Skill not found error

**Solution:**
- Verify skill is registered in skills.yaml
- Check skill directory exists
- Verify SKILL.md file exists
- Check skill is enabled

### Validation Failed

**Problem:** Skill validation failed

**Solution:**
- Check all required sections are present
- Verify version is present (for declarative skills)
- Check heading format
- Review section names

### Execution Failed

**Problem:** Skill execution failed

**Solution:**
- Check tool dependencies
- Verify OS v2 components are available
- Review error logs
- Check fallback conditions

## Skill Performance

Skills are optimized for performance:
- Heading normalization cache
- Lazy skill loading
- Efficient validation
- Parallel tool execution (where applicable)

## Skill Security

Skills implement security measures:
- Input validation
- Capability enforcement
- Sandbox execution
- Error sanitization
- Audit logging

## Skill Future Enhancements

### Planned Features

- **Skill Composition**: Compose skills from other skills
- **Skill Templates**: Reusable skill templates
- **Skill Marketplace**: Share and discover skills
- **Skill Versioning**: Automatic version management
- **Skill Dependencies**: Explicit dependency management
- **Skill Testing**: Automated skill testing
