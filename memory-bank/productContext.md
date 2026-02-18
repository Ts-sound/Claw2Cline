# Product Context

## Why This Project Exists

Claw2Cline addresses a critical gap in AI agent orchestration: the inability to efficiently handle long-running tasks between different AI systems. When OpenClaw needs to delegate complex engineering work to Cline, traditional synchronous approaches block the calling agent, wasting resources and limiting parallelism.

## Problems It Solves

1. **Long-Running Task Blocking**: Without Claw2Cline, OpenClaw would need to wait synchronously for Cline to complete tasks, potentially timing out or blocking other operations.

2. **Lack of Feedback Loop**: No standardized way for Cline to report completion back to OpenClaw.

3. **Agent Isolation**: OpenClaw and Cline operate independently without a communication bridge.

## How It Works

### Workflow

1. **Dispatch**: OpenClaw triggers a Skill that sends a task JSON to Claw2Cline via WebSocket

2. **Acknowledge**: Claw2Cline receives the task and immediately responds with `{"status": "executing"}`

3. **Execute**: Claw2Cline spawns a Python subprocess to invoke Cline CLI commands

4. **Notify**: When Cline completes, Claw2Cline captures output and executes:

   ```bash
   openclaw agent --agent main --message "task done: [result]"
   ```

### Architecture Modes

- **Server Mode (Cline Manager)**: Manages Cline instances and task execution

- **Client Mode (OpenClaw Forwarder)**: Receives and forwards messages from OpenClaw

## User Experience Goals

- **Seamless Integration**: OpenClaw users should not need to understand the underlying complexity

- **Reliable Delivery**: Tasks must be acknowledged and completed reliably

- **Clear Feedback**: Status updates and completion notifications should be timely and accurate

- **Scalable**: Foundation for future multi-agent cluster support