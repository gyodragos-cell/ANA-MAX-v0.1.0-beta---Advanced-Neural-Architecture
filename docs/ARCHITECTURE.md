# ANA MAX Architecture

## Overview
ANA MAX is a sophisticated AI agent system designed for local-first operation with advanced tool orchestration, multi-backend support, and comprehensive monitoring capabilities.

## Core Components

### 1. Agent System (`agents/`)
- **Agent orchestration** and lifecycle management
- Multi-agent coordination patterns
- Session management and persistence

### 2. Core System (`core/`)
- **Backends**: Multiple AI backend support (Ollama, OmniRoute, OpenRouter)
- **Agent**: Main agent logic and state management
- **Native Telemetry**: Frida-based system instrumentation
- **Event Streaming**: Real-time event handling
- **Context Management**: Workspace and conversation context

### 3. Tools (`tools/`)
- **140+ tools** for various operations:
  - File operations and editing
  - Terminal and command execution
  - Desktop automation and UI control
  - Network and security testing
  - Vision and OCR capabilities
  - Memory and learning systems
  - Code analysis and debugging

### 4. Bridge System (`bridge/`)
- **Direct Bridge**: Local tool execution without remote dependencies
- **Health Monitoring**: System health checks and diagnostics
- **Performance Tracking**: Latency and resource monitoring

### 5. Kernel (`ana_kernel/`)
- **Core Services**: Shell, LLM, filesystem operations
- **Self-Repair**: Automatic error recovery mechanisms
- **Scheduler**: Task scheduling and prioritization

### 6. Distributed System (`distributed/`)
- **Message Envelopes**: Structured inter-component communication
- **Transport Layers**: Multiple transport implementations (local, fake)
- **Replication**: Best-effort message replication
- **Conflict Resolution**: Last-write-wins conflict handling

### 7. Memory System (`memory/`)
- **Vector Memory**: Semantic search and retrieval
- **Session Checkpoints**: Persistent state management
- **Conversation Learning**: Learning from past interactions
- **ANA Memory**: Long-term project knowledge storage

### 8. Dashboard (`dashboard/`)
- **Web Interface**: Real-time monitoring and control
- **Metrics Display**: Performance and health metrics
- **Interactive Controls**: Manual intervention capabilities

## Backend Architecture

### Supported Backends
1. **Ollama**: Local LLM inference (qwen2.5-coder:7b)
2. **OmniRoute**: External API routing (deepseek-v4-flash-free)
3. **OpenRouter**: Cloud-based model access

### Backend Selection
- Configurable via `config/settings.yaml`
- Primary/fallback backend support
- Automatic failover mechanisms

## Tool Architecture

### Tool Categories
- **File Operations**: Reading, writing, editing files
- **System Control**: Terminal, process management
- **Desktop Automation**: UI control, screenshots
- **Network**: Pentesting, MITM, scanning
- **Vision**: OCR, image analysis
- **Development**: Code analysis, debugging
- **Memory**: Learning, context management

### Tool Registry
- Lazy loading for performance
- Automatic dependency resolution
- Health monitoring and status tracking

## Data Flow

1. **User Input** → Agent Processing
2. **Tool Selection** → Tool Router (LLM or Regex)
3. **Tool Execution** → Direct Bridge
4. **Result Processing** → Context Update
5. **Response Generation** → Backend LLM
6. **Output** → User Display

## Security Architecture

### Local-First Design
- All processing happens locally by default
- No external dependencies for core functionality
- User-controlled network access

### Frida Integration
- Process instrumentation for security testing
- System-level monitoring capabilities
- Desktop automation support

## Performance Optimization

### Caching
- Tool result caching
- Context state caching
- Model response caching

### Lazy Loading
- Tool modules loaded on demand
- Backend connections established when needed
- Resource cleanup on idle

### Monitoring
- Real-time performance metrics
- Health check endpoints
- Error tracking and alerting

## Configuration

### Main Config (`config/settings.yaml`)
- Backend selection
- Tool permissions
- System limits
- Feature flags

### Environment Variables
- API keys (optional)
- Model configurations
- Debug settings

## Deployment

### Local Development
- Python 3.12+ required
- Virtual environment recommended
- Ollama for local LLM

### Production
- Docker support available
- Health check endpoints
- Graceful shutdown handling

## Monitoring and Observability

### Logs
- Structured logging with levels
- Component-specific log files
- Error tracking and aggregation

### Metrics
- Tool execution latency
- Backend response times
- Resource utilization
- Error rates

### Health Checks
- System health endpoints
- Component status monitoring
- Automatic failure detection

## Extensibility

### Adding New Tools
- Implement Tool interface
- Add to tool registry
- Update permissions if needed

### Adding New Backends
- Implement backend interface
- Add to backend selection logic
- Update configuration schema

### Custom Plugins
- Plugin system for extensions
- Hook points for custom logic
- Configuration management

## Known Limitations

1. **GPU Requirements**: Some features require CUDA-capable GPU
2. **Memory Usage**: Large models require significant RAM
3. **Windows Focus**: Desktop automation is Windows-specific
4. **Model Stability**: Some external models may be unstable

## Future Roadmap

- Enhanced distributed capabilities
- Improved multi-agent coordination
- Better GPU optimization
- Expanded plugin ecosystem
- Enhanced security features
