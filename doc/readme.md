# Claw2Cline 整体设计

## 架构概览

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  OpenClaw   │─────►│    cli      │─────►│   clientd   │─────►│   server    │
│   (Skill)   │◄─────│  (命令行)    │◄─────│  (代理进程)  │◄─────│  (任务调度)  │
└─────────────┘      └─────────────┘      └─────────────┘      └──────┬──────┘
                                                                       │
                                                                       ▼
                                                                 ┌─────────────┐
                                                                 │   Cline     │
                                                                 │  (CLI进程)   │
                                                                 └─────────────┘
```

## 模块说明

### 1. server (服务端)
- **职责**: WebSocket 服务端，管理 Cline 子进程
- **功能**:
  - 监听 WebSocket 连接
  - 接收任务请求
  - 启动/监控 Cline 子进程
  - 返回任务执行状态和结果

### 2. clientd (客户端守护进程)
- **职责**: WebSocket 客户端，OpenClaw 通信代理
- **功能**:
  - 连接 server WebSocket
  - 监听命名管道
  - 转发任务请求和响应
  - 管理缓存目录

### 3. cli (命令行工具)
- **职责**: 用户/OpenClaw 交互入口
- **功能**:
  - 解析命令行参数
  - 通过命名管道与 clientd 通信
  - 输出响应结果

## 通信机制

### 命名管道 (cli <-> clientd)

缓存目录: `~/.claw2cline/`

```
~/.claw2cline/
├── request.pipe    # cli -> clientd (发送任务请求)
├── response.pipe   # clientd -> cli (接收响应结果)
└── pid             # clientd 进程 PID 文件
```

### WebSocket (clientd <-> server)

- 协议: WebSocket
- 格式: JSON
- 默认端口: 8765

## 消息协议

### 请求消息

```json
{
  "id": "uuid-v4",
  "type": "task",
  "session": "default",
  "command": "cline --prompt 'your task'",
  "timestamp": 1234567890
}
```

### 响应消息

```json
{
  "id": "uuid-v4",
  "status": "executing|successed|failed",
  "output": "task output or error message",
  "timestamp": 1234567890
}
```

## 执行流程

1. **启动阶段**
   - server 启动，监听 WebSocket 端口
   - clientd 启动，创建命名管道，连接 server

2. **任务执行**
   - OpenClaw 调用: `claw2cline send "task description"`
   - cli 写入请求到 `request.pipe`
   - clientd 读取请求，通过 WebSocket 发送给 server
   - server 立即回复 `{"status": "executing"}`
   - clientd 将状态写入 `response.pipe`
   - cli 输出状态给 OpenClaw

3. **任务完成**
   - server 监控 Cline 进程
   - 进程结束，server 发送结果 `{"status": "successed|failed"}`
   - clientd 接收结果，写入 `response.pipe`

## 配置

环境变量:
- `CLAW2CLINE_SERVER_URL`: WebSocket 服务端地址 (默认: `ws://localhost:8765`)
- `CLAW2CLINE_CACHE_DIR`: 缓存目录 (默认: `~/.claw2cline`)

## 使用示例

```bash
# 启动服务端
claw2cline server

# 启动客户端守护进程
claw2cline clientd

# 发送任务
claw2cline send "实现一个 HTTP 服务器"

# 指定 session
claw2cline send --session dev "修复登录 bug"