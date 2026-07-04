# Agent Skill Board

一个轻量的本地 Agent Skills 看板，用来管理 Claude Code、Codex、Hermes 等工具共享的 `SKILL.md` 技能库。

Agent Skill Board 会递归扫描技能目录，把所有 `SKILL.md` 以卡片形式展示出来，并自动识别可能适用的宿主、健康状态、使用状态和标签。它不需要数据库，也不需要前端构建工具，只有一个 Python 标准库脚本。

English documentation is available below.

## 功能

- 递归扫描所有 `SKILL.md`。
- 自动跳过 `.git`、`node_modules`、缓存、归档等噪音目录。
- 展示名称、简介、版本、相对路径、宿主徽标、健康状态、使用次数和标签。
- 自动识别技能大概率适用于 Hermes、Claude Code、Codex，还是通用 Agent Skill。
- 可读取可选的侧车文件：
  - `.skill-tags.json`
  - `.skill-desc-zh.json`
  - `.usage.json`
- 支持在网页里给 skill 打标签。
- 支持从网页打开本地 `SKILL.md` 或所在目录，但只允许打开配置的技能目录内部路径。
- 提供简单 JSON API，方便本地自动化。
- 零第三方 Python 依赖。

## 快速开始

```bash
git clone https://github.com/Sukerr/agent-skill-board.git
cd agent-skill-board
python3 skill_board.py
```

打开：

```text
http://127.0.0.1:8777/
```

默认扫描目录：

```text
~/ai-workspace/shared-skills
```

你可以用环境变量指定自己的技能目录和端口：

```bash
SKILL_BOARD_SKILLS_DIR="$HOME/.agents/skills" \
SKILL_BOARD_PORT=8788 \
python3 skill_board.py
```

可选环境变量：

| 变量 | 默认值 |
| --- | --- |
| `SKILL_BOARD_SKILLS_DIR` | `~/ai-workspace/shared-skills` |
| `SKILL_BOARD_ICLOUD_DIR` | `~/Library/Mobile Documents/com~apple~CloudDocs/ai-skills` |
| `SKILL_BOARD_HOST` | `127.0.0.1` |
| `SKILL_BOARD_PORT` | `8777` |

## 侧车文件

没有侧车文件也可以正常使用。如果技能目录里存在这些文件，看板会自动读取：

```text
.skill-tags.json
.skill-desc-zh.json
.usage.json
```

在网页里编辑标签时，会写回 `.skill-tags.json`。

看板只会打开 `SKILL_BOARD_SKILLS_DIR` 内部的文件或目录。网页界面不会删除、归档、同步或发布 skill。

## API

```text
GET  /
GET  /api/skills
GET  /api/status
POST /api/tags
POST /api/open
```

`POST /api/tags`:

```json
{
  "skill": "demo-skill",
  "tags": ["example", "workflow"]
}
```

`POST /api/open`:

```json
{
  "kind": "file",
  "path": "/absolute/path/inside/skills/SKILL.md"
}
```

## 示例 Skill

见 `examples/skills/demo-skill/SKILL.md`。

## 同步脚本模板

`scripts/` 目录里有可选的同步脚本模板，可以把技能目录同步到另一个本地目录或 iCloud 目录。使用前请先按自己的环境检查和修改。

## 安全提醒

不要未经检查就公开自己的真实 skills 目录。技能文件里经常会包含本机路径、私有基础设施说明、用户名、内部 URL 或个人工作流细节。更多说明见 `SECURITY.md`。

## 许可证

MIT

---

## English

A tiny local dashboard for managing Agent Skills across tools such as Claude Code, Codex, and Hermes.

Agent Skill Board scans a folder of `SKILL.md` files, shows them as searchable cards, detects likely host compatibility, surfaces health and usage metadata, and lets you tag skills without introducing a database or frontend build step.

It is a single Python standard-library app.

## Features

- Recursively scans `SKILL.md` files.
- Skips common noise folders such as `.git`, `node_modules`, caches, and archives.
- Shows name, description, version, relative path, host badges, health badges, usage counts, and tags.
- Detects likely compatibility with Hermes, Claude Code, Codex, or generic skill usage.
- Reads optional sidecar files:
  - `.skill-tags.json`
  - `.skill-desc-zh.json`
  - `.usage.json`
- Supports local-only open actions for files and directories inside the configured skills folder.
- Exposes small JSON APIs for local automation.
- Requires no third-party Python packages.

## Quick Start

```bash
git clone https://github.com/Sukerr/agent-skill-board.git
cd agent-skill-board
python3 skill_board.py
```

Open:

```text
http://127.0.0.1:8777/
```

By default the app scans:

```text
~/ai-workspace/shared-skills
```

You can override paths and port with environment variables:

```bash
SKILL_BOARD_SKILLS_DIR="$HOME/.agents/skills" \
SKILL_BOARD_PORT=8788 \
python3 skill_board.py
```

Optional variables:

| Variable | Default |
| --- | --- |
| `SKILL_BOARD_SKILLS_DIR` | `~/ai-workspace/shared-skills` |
| `SKILL_BOARD_ICLOUD_DIR` | `~/Library/Mobile Documents/com~apple~CloudDocs/ai-skills` |
| `SKILL_BOARD_HOST` | `127.0.0.1` |
| `SKILL_BOARD_PORT` | `8777` |

## Sidecar Files

Agent Skill Board works without sidecar files. If present, it uses:

```text
.skill-tags.json
.skill-desc-zh.json
.usage.json
```

Tags are written back to `.skill-tags.json` when edited in the UI.

The app only opens files/directories inside `SKILL_BOARD_SKILLS_DIR`. It does not delete, archive, publish, or sync skills from the web UI.

## API

```text
GET  /
GET  /api/skills
GET  /api/status
POST /api/tags
POST /api/open
```

`POST /api/tags`:

```json
{
  "skill": "demo-skill",
  "tags": ["example", "workflow"]
}
```

`POST /api/open`:

```json
{
  "kind": "file",
  "path": "/absolute/path/inside/skills/SKILL.md"
}
```

## Example Skill

See `examples/skills/demo-skill/SKILL.md`.

## Sync Templates

The `scripts/` folder contains optional templates for syncing a skills folder to another local folder or iCloud-backed folder. Review and edit them before use.

## Security Notes

Do not publish your real skills folder without review. Skills often contain local paths, private infrastructure notes, usernames, internal URLs, or operational details. See `SECURITY.md`.

## License

MIT
