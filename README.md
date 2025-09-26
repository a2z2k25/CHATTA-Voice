```
██╗     ██╗██╗   ██╗██╗████████╗██╗   ██╗
██║     ██║██║   ██║██║╚══██╔══╝╚██╗ ██╔╝
██║     ██║██║   ██║██║   ██║    ╚████╔╝
██║     ██║╚██╗ ██╔╝██║   ██║     ╚██╔╝
███████╗██║ ╚████╔╝ ██║   ██║      ██║
╚══════╝╚═╝  ╚═══╝  ╚═╝   ╚═╝      ╚═╝


LIVITY 1.0 - Lightweight Agent Lifecycle Management
Building Unified Multi-agent Business Applications
```

# LIVITY - @bumba/agent-lifecycle

> 🏁 **PROFESSIONAL AGENT LIFECYCLE FRAMEWORK** - A lightweight FSM primitive for managing agent lifecycles with automatic timeouts and resource cleanup

**Core component of the BUMBA Platform** - Building Unified Multi-agent Business Applications

## Features

- 🟡 **Simple FSM** - Clean state transitions with validation
- 🟢 **Automatic Timeouts** - Per-state configurable timeouts
- 🔴 **Built-in Retry** - Exponential backoff on failures
- 🟠 **Metrics** - Track timing, transitions, and errors
- 🟡 **Health Monitoring** - Built-in diagnostics
- 🟢 **Event-Driven** - EventEmitter-based architecture
- 🔴 **Zero Dependencies** - Pure Node.js
- 🟠 **TypeScript Ready** - Full type definitions
- 🏁 **Production Tested** - Benchmarked at scale

## Installation

```bash
npm install @bumba/agent-lifecycle
```

## Quick Start

```javascript
const { AgentLifecycle, StateEvent } = require('@bumba/agent-lifecycle');

// Create an agent
const agent = new AgentLifecycle('task-processor', {
  maxActiveTime: 30000,  // 30 seconds
  maxRetries: 3
});

// Listen for state changes
agent.on('stateChange', ({ from, to, event }) => {
  console.log(`Agent transitioned: ${from} -> ${to} (${event})`);
});

// Run through lifecycle
await agent.transition(StateEvent.SPAWN, { task: 'process-data' });
await agent.transition(StateEvent.ACTIVATE, { taskCount: 5 });
// ... do work ...
await agent.transition(StateEvent.VALIDATE, { checksum: 'abc123' });
await agent.transition(StateEvent.COMPLETE, { result: 'success' });
```

## State Machine

```
╔═══════════════════════════════════════════════════════════════╗
║                     AGENT STATE FLOW                          ║
╚═══════════════════════════════════════════════════════════════╝

┌──────┐    SPAWN     ┌──────────┐   ACTIVATE   ┌────────┐
│ IDLE │─────────────►│ SPAWNING │─────────────►│ ACTIVE │
└──────┘              └──────────┘              └────────┘
                                                      │
                                                  VALIDATE
                                                      ▼
┌───────────┐  COMPLETE  ┌─────────────┐      ┌────────────┐
│ COMPLETED │◄───────────│ COMPLETING  │◄─────│ VALIDATING │
└───────────┘            └─────────────┘      └────────────┘
     🏁                                              🟠
```

| State | Department | Purpose | Timeout | Status |
|-------|------------|---------|---------|---------|
| `IDLE` | 🟡 Strategy | Waiting to start | 5 min default | Ready |
| `SPAWNING` | 🟢 Backend | Initializing | - | Active |
| `ACTIVE` | 🟢 Backend | Processing | 30 min default | Running |
| `VALIDATING` | 🟠 Testing | Verifying | 1 min default | Checking |
| `COMPLETING` | 🔴 Frontend | Cleanup | - | Finalizing |
| `COMPLETED` | 🏁 Complete | Finished | - | Done |

## Configuration

```javascript
const agent = new AgentLifecycle('my-agent', {
  maxIdleTime: 300000,        // 5 minutes
  maxActiveTime: 1800000,      // 30 minutes
  maxValidationTime: 60000,    // 1 minute
  maxRetries: 3,               // Retry attempts
  autoComplete: true           // Auto-complete on timeout
});
```

## Orchestration

Manage multiple agents:

```javascript
const { AgentOrchestrator } = require('@bumba/agent-lifecycle');

const orchestrator = new AgentOrchestrator({
  maxAgents: 50,
  defaultAgentConfig: {
    maxActiveTime: 60000
  }
});

// Create agents
const agent1 = orchestrator.createAgent('worker-1');
const agent2 = orchestrator.createAgent('worker-2');

// Monitor all agents
orchestrator.on('agent:stateChange', ({ agentId, from, to }) => {
  console.log(`${agentId}: ${from} -> ${to}`);
});

// Get metrics
const metrics = orchestrator.getMetrics();
console.log(`Active agents: ${metrics.activeAgents}/${metrics.totalAgents}`);

// Graceful shutdown
await orchestrator.completeAll('shutdown');
```

## API

### Core Methods
```javascript
// AgentLifecycle
transition(event, data?)    // Change state
getState()                   // Current state
getStatistics()              // Runtime metrics
forceComplete(reason?)       // Force completion

// AgentOrchestrator
createAgent(id, config?)     // Create agent
getAgent(id)                 // Get by ID
getMetrics()                 // System metrics
completeAll(reason?)         // Graceful shutdown
```

### Events
- `stateChange` - Any transition
- `enter:<state>` - State entry
- `lifecycle:started/ended` - Lifecycle events

## Common Patterns

### Job Processing
```javascript
const agent = new AgentLifecycle('worker', {
  maxActiveTime: 300000
});

await agent.transition(StateEvent.SPAWN);
await agent.transition(StateEvent.ACTIVATE, { taskCount: 10 });
// Process work...
await agent.transition(StateEvent.COMPLETE);
```

### Multi-Agent System
```javascript
const orchestrator = new AgentOrchestrator({ maxAgents: 100 });

const agent = orchestrator.createAgent('worker-1');
await agent.transition(StateEvent.ACTIVATE);
// Coordinate agents...
await orchestrator.completeAll('shutdown');
```

## Health Check

```javascript
app.get('/health', (req, res) => {
  const health = orchestrator.getHealth();
  const status = health.status === 'healthy' ? 200 : 503;
  res.status(status).json(health);
});
```

## Debugging

```bash
DEBUG=agent-lifecycle node app.js
```

## Performance

- Single agent: ~0.5ms overhead
- 100 agents: ~50ms
- 10K transitions: ~200ms

## Testing

```bash
npm test          # Run tests
npm run benchmark  # Performance tests
```

## License

MIT

## Building Blocks

LIVITY is designed as a low-level primitive that can be composed into larger systems. It provides the foundational state machine logic that more complex agent frameworks can build upon, keeping your architecture modular and maintainable.

---


🏁 BUMBA PLATFORM 🏁
Building Unified Multi-agent Business Applications

🟡 ProductStrategist • 🟢 BackendEngineer
🔴 DesignEngineer • 🟠 Testing • 🏁 Complete

**LIVITY 1.0** • Professional Agent Lifecycle Management • MIT License

---

🏁 **LIVITY** powers distributed agent orchestration in production at scale.
