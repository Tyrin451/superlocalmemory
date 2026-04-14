# Skill Evolution — SuperLocalMemory

> Track, analyze, and evolve your AI agent skills automatically.

---

## What Is Skill Evolution?

Skill Evolution turns SuperLocalMemory from a passive memory system into an active learning engine that tracks how your skills perform and helps them improve over time.

**The problem:** AI agent skills (SKILL.md files, slash commands, agent definitions) are static. A skill installed today works the same way 6 months from now — even if it failed 50 times, even if a better approach was discovered.

**The solution:** SLM observes every skill invocation, builds execution traces, computes performance metrics, and surfaces insights so you (and eventually the system itself) can evolve skills based on real data.

---

## How It Works

```
Your session
  │
  │ SLM hook captures every tool call (enriched: input, output, session, project)
  ▼
tool_events table (rich execution data)
  │
  │ SkillPerformanceMiner runs during consolidation
  ▼
Per-skill metrics + behavioral assertions + skill entities
  │
  │ Next session's soft prompts include skill routing recommendations
  ▼
Smarter skill selection, session by session
```

### Three Data Sources

| Source | What It Captures | Cost |
|--------|-----------------|------|
| **SLM Hook** (primary) | Every tool call with input/output (500 chars), session ID, project path. Secret scrubbing built-in. | Zero — runs locally, no LLM calls |
| **ECC Integration** (optional) | Rich observations from [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) via `slm ingest --source ecc` | Zero — reads existing ECC data |
| **Consolidation Pipeline** | Mines tool_events for patterns, creates assertions, updates skill entities | Zero — statistical analysis only |

### What Gets Tracked Per Skill

| Metric | Description |
|--------|-------------|
| **Invocation count** | How many times the skill was used |
| **Effective score** | Approximate success rate based on execution trace analysis |
| **Session count** | How many sessions used this skill |
| **Skill correlations** | Which skills are frequently used together |

### Outcome Heuristic

SLM uses a conservative, approximate heuristic to determine if a skill invocation was effective:

| Signal | Type | What It Means |
|--------|------|---------------|
| Productive tools follow (Edit, Write, Bash success) | Positive | Skill likely helped |
| Same skill re-invoked within 5 minutes | Negative | Likely retry = failure |
| Bash errors in next 3 tool events | Negative | Something went wrong |
| Session continues 10+ events | Weak positive | User stayed engaged |

These signals are labeled as **approximate** everywhere. They inform soft prompt routing but do not trigger automatic changes without human review.

---

## Dashboard: Skill Evolution Tab

The dedicated **Skill Evolution** tab in the SLM dashboard shows:

- **Overview cards** — Total skill events, unique skills, performance assertions, skill correlations
- **Skill performance cards** — Per-skill effective score, invocation count, confidence level
- **Skill correlations** — Which skills work well together
- **Compatibility notice** — Current IDE support status

Access: Open `http://localhost:8765` and navigate to the Skill Evolution tab in the sidebar.

---

## IDE Compatibility

| IDE | Status | How |
|-----|--------|-----|
| **Claude Code** | Supported | SLM hook auto-registered via `slm init` |
| **Cursor** | Planned | Adapter needed |
| **Windsurf** | Planned | Adapter needed |
| **VS Code Copilot** | Planned | Extension events adapter needed |
| **JetBrains** | Planned | Adapter needed |
| **Any IDE** | API available | POST to `/api/v3/tool-event` directly |

The backend (API, miner, database, dashboard) is fully IDE-agnostic. Any client that POSTs tool events to the `/api/v3/tool-event` endpoint gets full benefit. The hook that ships with SLM is currently optimized for Claude Code.

### API Endpoint

```bash
POST http://localhost:8765/api/v3/tool-event
Content-Type: application/json

{
  "tool_name": "Skill",
  "event_type": "complete",
  "input_summary": "{\"skill\": \"my-skill-name\", \"args\": \"...\"}",
  "output_summary": "{\"success\": true}",
  "session_id": "your-session-id",
  "project_path": "/path/to/project"
}
```

All fields except `tool_name` are optional. Existing integrations that send only `tool_name` + `event_type` continue to work.

---

## ECC Integration

[Everything Claude Code (ECC)](https://github.com/affaan-m/everything-claude-code) is a popular plugin for Claude Code that provides continuous learning, instinct-based pattern detection, and a rich observation pipeline.

SLM's skill observation patterns were inspired by ECC's architecture. If you have ECC installed, you can enrich SLM's skill tracking with ECC's deeper observations:

```bash
# One-time import of existing ECC observations
slm ingest --source ecc

# Preview without writing (dry run)
slm ingest --source ecc --dry-run
```

This reads ECC's observation files from `~/.claude/homunculus/projects/*/observations.jsonl` and imports them into SLM's `tool_events` table with full input/output preservation.

**ECC is not required.** SLM is fully self-sufficient — its own hook captures all the data needed for skill tracking. ECC integration is an optional enhancement for users who want both systems working together.

---

## Configuration

### Enable/Disable Skill Tracking

Skill tracking is enabled by default when the SLM hook is registered. To check:

```bash
slm status  # Shows hook registration status
```

### Consolidation

Skill performance mining runs as Step 10 in the consolidation pipeline. It processes only new events since the last run (incremental). To trigger manually:

```bash
slm consolidate --cognitive
```

### Minimum Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| MIN_INVOCATIONS | 5 | Minimum uses before creating assertions |
| MIN_CONFIDENCE | 0.5 | Minimum confidence for soft prompt injection |
| TRACE_WINDOW | 10 | Tool events to analyze after each Skill call |
| RETRY_WINDOW | 300s | Same Skill within this window = potential retry |

These are conservative by design — we'd rather miss a pattern than hallucinate one.

---

## Research Foundations

SLM's skill evolution system draws from:

- **[EvoSkills](https://arxiv.org/abs/2604.01687)** (HKUDS, 2026) — Co-evolutionary verification with information isolation. +30pp improvement from blind verification.
- **[OpenSpace](https://github.com/HKUDS/OpenSpace)** (HKUDS, MIT) — 3-trigger evolution system (post-analysis + tool degradation + metric monitor). Anti-loop guards. Version DAG model.
- **[SkillsBench](https://arxiv.org/abs/2602.12670)** (2026) — 86-task benchmark showing self-generated skills provide zero benefit without verification. Focused 2-3 module skills outperform exhaustive docs.
- **[SoK: Agent Skills](https://arxiv.org/abs/2602.12430)** (2026) — Four-axis taxonomy. Skills and MCP are orthogonal layers.

---

## What's Next

- **C2: Arsenal Evolution Engine** — Automatic skill mutation with 3-trigger system, LLM confirmation gate, and blind verification. Evolved skills stored in `~/.claude/skills/evolved/`.
- **C3: SLM Productization** — New MCP tools (`evolve_skill`, `skill_health`, `skill_lineage`), new fact types, full dashboard evolution history.
- **IDE Adapters** — Cursor, Windsurf, VS Code Copilot, JetBrains support.

---

## Links

- [SLM GitHub](https://github.com/qualixar/superlocalmemory)
- [Qualixar](https://qualixar.com)
- [Everything Claude Code](https://github.com/affaan-m/everything-claude-code)
- [OpenSpace](https://github.com/HKUDS/OpenSpace)
- [EvoSkills Paper](https://arxiv.org/abs/2604.01687)
