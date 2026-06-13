---
name: SuperPmAgent-gen-feishu-design
description: Apply when a PM has written a requirements document in Feishu and wants an architecture design doc, task assignment doc, and Bitable task tracker auto-generated. This skill produces design artifacts only — code implementation is handled by subsequent /goal runs against the Bitable tasks.
argument-hint: "Feishu requirement doc URL or token, target folder token"
---

# Gen Feishu Design

Use this pattern when a PM finishes a Feishu requirements document and wants design artifacts generated automatically.

## Clarify

- Which Feishu document contains the requirements? (URL or doc token)
- Which Feishu folder should the output documents be created in? (folder token)
- Are there any specific technical constraints or team preferences to apply?
- Should the Bitable task tracker be created in the same folder or a separate workspace?

## Likely Touchpoints

- **Feishu Docs** — read requirement doc via `lark-cli docs +fetch`, create architecture + assignment docs via `lark-cli docs +create`
- **Feishu Base (Bitable)** — create task tracker table, fields, batch-insert records, configure views via `lark-cli base`
- **SuperPmAgent Knowledge** — read `profiles/` for team skill tags to drive task assignment recommendations
- **No code changes** — this skill produces design artifacts only. Code implementation is delegated to subsequent `/goal` runs

## Prerequisites

- `lark-cli` installed and authenticated (`npx @larksuite/cli@latest install` + `lark-cli auth login --recommend`)
- SuperPmAgent profiles populated with member skill tags (used for task assignment recommendations)
- Target Feishu folder exists and is accessible

## Flow

### 1. Read Requirements

```bash
lark-cli docs +fetch --api-version v2 --doc "<requirement doc URL or token>"
```

Output is XML format. Extract from the returned `<title>`, `<h1>`-`<h3>`, `<p>`, `<ul><li>`, `<table>` blocks: functional scope, acceptance criteria, non-functional constraints, domain entities, user roles.

### 2. Generate Architecture Design Document

Produce a Feishu doc with 8 fixed sections using Mermaid diagrams (rendered natively in Feishu):

```
# [需求名] - 架构设计文档

## 1. 需求概述 (business context, scope, non-functional constraints)
## 2. 架构总览 (architecture style + rationale, C4 Context diagram, C4 Container diagram)
## 3. 模块划分 (module table: name | responsibility | inputs | outputs | dependencies)
## 4. 数据模型 (ER diagram via Mermaid erDiagram, key table structures, cache strategy)
## 5. API 设计 (endpoint table: method | path | request | response | error codes)
## 6. 技术选型 (technology table: name | version | purpose | rationale)
## 7. 架构决策记录 (ADR per key decision: Context → Decision → Consequences → Alternatives)
## 8. 风险与缓解 (risk table: description | impact | probability | mitigation)
```

Create via (XML format — `lark-cli` v2 API uses XML, not Markdown, for document content):

```bash
lark-cli docs +create --api-version v2 \
  --folder-token "<target folder token>" \
  --content '<title>[需求名] - 架构设计文档</title>
<h1>1. 需求概述</h1>
<p>业务背景、功能范围、非功能约束...</p>
<h1>2. 架构总览</h1>
<p>架构风格 + 选型理由</p>
<whiteboard type="mermaid">graph TD\n  A[Client] --> B[API]</whiteboard>
<h1>3. 模块划分</h1>
<table>...</table>
...'
```

**XML tag reference** (v2 API):

| XML Tag | 对应飞书元素 |
|---|---|
| `<title>` | 文档标题 |
| `<h1>` ~ `<h3>` | 标题层级 |
| `<p>` | 段落 |
| `<ul><li>` | 无序列表 |
| `<ol><li>` | 有序列表 |
| `<table><tr><td>` | 表格 |
| `<callout>` | 高亮框 |
| `<whiteboard type="mermaid">` | Mermaid 图表 |
| `<img href="URL"/>` | 网络图片 |
| `<hr/>` | 分隔线 |

> ⚠️ **重要**：`+create` 只建骨架（标题 + 各级标题 + 占位摘要）。完整正文内容用 `docs +update --api-version v2 --command append --content '...'` 分段追加写入。超长 `--content` 会触发字符限制。

### 3. Generate Task Assignment Document

Produce a Feishu doc with 4 sections:

```
# [需求名] - 分工方案

## 1. 任务拆解 (WBS table: WBS编号 | 任务 | 预估工时(≤8h) | 依赖 | 交付物)
## 2. 人员分配 (assignment table: 任务 | 推荐负责人 | 匹配技能 | 置信度 | 备选)
## 3. 时间线 (Mermaid Gantt chart)
## 4. 风险标注 (risk table: 风险任务 | 风险类型 | 建议)
```

**Assignment logic**: match task tech stack keywords against `knowledge/profiles/` member skill tags. Assign highest-match member. Confidence < 0.7 → mark "待PM指定". Output is a **recommendation** — PM reviews and confirms via Feishu comments.

Create via same `lark-cli docs +create` command.

### 4. Create Bitable Task Tracker

Create a single Bitable base with one task table (fine-grained: each task ≤ 8h, directly executable as a `/goal`):

```bash
# 4a. Create base (auto-creates a default table "数据表" with basic fields)
lark-cli base +base-create --name "[需求名]-任务跟踪"

# 4b. List tables to get table ID
lark-cli base +table-list --base-token <token>

# 4c. Add missing fields (type values are strings, not numeric codes!)
lark-cli base +field-create --base-token <token> --table-id <id> \
  --json '{"field_name":"所属阶段","type":"select"}'
lark-cli base +field-create --base-token <token> --table-id <id> \
  --json '{"field_name":"负责人","type":"user"}'
lark-cli base +field-create --base-token <token> --table-id <id> \
  --json '{"field_name":"预估工时(h)","type":"number"}'
lark-cli base +field-create --base-token <token> --table-id <id> \
  --json '{"field_name":"关联文档","type":"link"}'
lark-cli base +field-create --base-token <token> --table-id <id> \
  --json '{"field_name":"验收标准","type":"text"}'
lark-cli base +field-create --base-token <token> --table-id <id> \
  --json '{"field_name":"阻塞原因","type":"text"}'

# 4d. Write task records (one per command)
lark-cli base +record-upsert --base-token <token> --table-id <id> \
  --json '{"文本":"W-1.1 用户调研","单选":"P1 高","状态":"待办","预估工时(h)":4,"验收标准":"完成用户访谈报告"}'
# Repeat per task...
```

**Field schema (type = API string, not numeric):**

| Field | type | Notes |
|---|---|---|
| 任务名称 | `"text"` | WBS编号 + 任务描述 (default table 已有 "文本" 字段) |
| 所属阶段 | `"select"` | 需求分析 / 系统设计 / 开发 / 测试 / 部署 |
| 负责人 | `"user"` | Feishu real member (required for @notifications) |
| 优先级 | `"select"` | P0 紧急 / P1 高 / P2 中 / P3 低 (default table 已有 "单选" 字段) |
| 状态 | `"select"` | 待办 → 进行中 → 已完成 → 阻塞 |
| 截止时间 | `"datetime"` | Precision to day (default table 已有 "日期" 字段) |
| 预估工时(h) | `"number"` | Hours |
| 关联文档 | `"link"` | Link to architecture design doc |
| 验收标准 | `"text"` | One-sentence deliverable description |
| 阻塞原因 | `"text"` | Only filled when status = 阻塞 |

**Auto-configured views**: kanban (by status), calendar (by deadline), "My Tasks" (filter: 负责人 = current user).

### 5. Output Summary

Return:

```text
Generated:
- Architecture design doc: <URL>
- Task assignment doc: <URL>
- Bitable task tracker: <URL>
- Task count: <N> tasks across <M> phases
- Tasks needing PM assignment (confidence < 0.7): <list>

Next step: PM reviews assignment doc → confirms via comments → triggers /goal per Bitable task.
```

## Distill After Success

Capture:
- Architecture patterns that proved effective → `knowledge/domain/_shared/foundations/`
- Template refinements (sections that were most/least useful) → `knowledge/domain/_shared/conventions/`
- Skill tag matching accuracy (profiles → task mapping quality) → update profiles if gaps found
- Edge cases: requirements that were too ambiguous to generate design, Bitable API limits hit with large task counts
