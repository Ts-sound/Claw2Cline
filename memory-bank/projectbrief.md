# Claw2Cline Project Brief

## Project Overview

**Claw2Cline** is an asynchronous WebSocket bridge designed to facilitate seamless task delegation between OpenClaw and Cline. It enables OpenClaw to dispatch complex engineering missions to Cline's CLI through a high-performance Python bridge.

## Core Requirements

1. **WebSocket Communication**: Real-time bi-directional communication between OpenClaw and Cline
2. **Asynchronous Task Execution**: Handle long-running tasks without blocking
3. **Notification System**: Automatic reporting of task completion back to OpenClaw
4. **CLI Integration**: Interface with Cline's CLI for task execution

## Key Goals

- Solve the "long-running task" problem in agent collaboration
- Implement asynchronous notification pattern
- Enable closed-loop autonomous development workflow
- Support multi-cline agent cluster scheduling (future)

## Scope

### In Scope

- WebSocket server for receiving tasks from OpenClaw
- WebSocket client for forwarding messages
- Task execution via Cline CLI
- Completion notification back to OpenClaw

### Out of Scope (Future)

- Multi-cline agent cluster allocation and scheduling