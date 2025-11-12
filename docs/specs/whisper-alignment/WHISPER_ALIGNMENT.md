# Complete Alignment Recommendations Summary

## Three-Layer Architecture
1. **CLI Layer** (`cli.py`) - User commands
2. **MCP Layer** (`tools/`) - LLM tools  
3. **Core Layer** (`models.py`) - Shared logic

## Recommended Changes by Layer

### Core Layer (`models.py`)
| Current | Recommended | Reason |
|---------|-------------|---------|
| `get_current_model()` | `get_active_model()` | Match CLI "active" terminology |
| `set_current_model()` | `set_active_model()` | Match CLI "active" terminology |
| `is_model_installed()` | `is_whisper_model_installed()` | Explicit namespace |
| `get_installed_models()` | `get_installed_whisper_models()` | Clearer scope |
| `has_coreml_model()` | `has_whisper_coreml_model()` | Namespace clarity |
| `WHISPER_MODELS` | `WHISPER_MODEL_REGISTRY` | Better describes purpose |
| ❌ Missing | `remove_whisper_model()` | Support removal feature |
| ❌ Missing | `benchmark_whisper_model()` | Support benchmarking |

### MCP Layer (Tools)
| Current | Recommended | Reason |
|---------|-------------|---------|
| `download_model()` | `whisper_model_install()` | Match CLI pattern |
| `whisper_list_models()` | `whisper_models()` | Match CLI command |
| Duplicate list functions | Consolidate to one | Remove confusion |
| ❌ Missing | `whisper_model_active()` | Match CLI feature |
| ❌ Missing | `whisper_model_remove()` | Match CLI feature |
| ❌ Missing | `whisper_model_benchmark()` | New feature |

### CLI Layer
| Current | Status | Notes |
|---------|--------|-------|
| `whisper models` | ✅ Good | Keep as-is |
| `whisper model active` | ✅ Good | Keep as-is |
| `whisper model install` | ✅ Good | Keep as-is |
| `whisper model remove` | ✅ Good | Keep as-is |
| ❌ Missing benchmark | Add `whisper model benchmark` | New feature |

## Implementation Priority

### Phase 1: Core Alignment (Foundation)
1. Rename core functions to use "active" instead of "current"
2. Add whisper prefix to core functions for clarity
3. Add missing core functions (remove, benchmark)

### Phase 2: MCP Tool Alignment
1. Rename MCP tools to match CLI patterns
2. Consolidate duplicate list functions
3. Add missing MCP tools (active, remove)

### Phase 3: New Features
1. Add benchmark functionality to all layers
2. Add any other optimization tools

## Benefits of Alignment

1. **Consistency**: Same terminology across all layers
2. **Discoverability**: Predictable naming patterns
3. **Maintainability**: Clear relationships between layers
4. **User Experience**: CLI and MCP behave identically
5. **Developer Experience**: Easy to understand codebase

## Example Flow After Changes

### Setting Active Model
```
CLI: voicemode whisper model active base
 ↓ calls
MCP: whisper_model_active("base") 
 ↓ calls
Core: set_active_model("base")
```

### Listing Models
```
CLI: voicemode whisper models
 ↓ calls
MCP: whisper_models()
 ↓ calls  
Core: get_installed_whisper_models(), get_active_model()
```

### Installing Model
```
CLI: voicemode whisper model install tiny
 ↓ calls
MCP: whisper_model_install("tiny")
 ↓ calls
Core: download logic + is_whisper_model_installed()
```

All three layers use consistent naming and terminology!