# Claw2Cline

**Claw2Cline**: An Asynchronous WebSocket Bridge for Orchestrating Cline via OpenClaw Skills.

Claw2Cline is a high-performance Python bridge designed to facilitate seamless task delegation between OpenClaw and Cline.

By leveraging WebSockets for real-time bi-directional communication, Claw2Cline allows OpenClaw to dispatch complex engineering missions to Cline's CLI. It features an asynchronous notification system that monitors task execution and automatically reports completion back to the OpenClaw agent, ensuring a closed-loop autonomous development workflow.

> Claw2Cline is a Python-based orchestration bridge that enables **OpenClaw** to command **Cline** via CLI. It solves the "long-running task" problem in agent collaboration by implementing an **asynchronous notification pattern**.
> By leveraging **WebSockets** for real-time bi-directional communication, Claw2Cline allows OpenClaw to dispatch complex engineering missions to Cline's CLI. It features an asynchronous notification system that monitors task execution and automatically reports completion back to the OpenClaw agent, ensuring a closed-loop autonomous development workflow.

## 🏗️ 方案设计：WebSocket 转发与异步通知机制

### 1. 业务流程 (Workflow)

1. **分发 (Dispatch):** OpenClaw 触发 Skill  通过 WebSocket 向 `Claw2Cline` 发送任务 JSON。
2. **确认 (Ack):** `Claw2Cline` 接收任务，立即回传 `{"status": "executing"}`，OpenClaw 收到“已开始执行”回复。
3. **执行 (Execution):** `Claw2Cline` 启动 Python 子进程调用 Cline CLI 指令。
4. **通知 (Notification):** Cline 任务结束，`Claw2Cline` 捕获输出，并执行命令：
`openclaw agent --agent main --message "task done: [result]"` 进行反向通知。

Claw2Cline 运行模式 (server(cline manage) , client(openclaw消息转发) )

---

## TODO
多cline agent 集群分配调度