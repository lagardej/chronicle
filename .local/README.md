# .local — Agent Scratchpad

This directory is the local runtime workspace for all agents.
It is **gitignored** (except this README). Contents are ephemeral and machine-local.
Nothing written here affects the tracked codebase.

## Structure

```md
.local/
├── README.md              ← this file (committed)
├── <role>/                ← the role
│   ├── SESSION.md         ← workflow: session state
│   ├── HANDOFF.md         ← workflow: output for next role
│   └── scratch/           ← free-form AI working space
└── ...
```

## Two areas per role

**Workflow files** — at `.local/<role>/`
Read by the human and optionally by other roles.

- `SESSION.md` — written at end of every session so the next session can resume.
- `HANDOFF.md` — written when output needs to be routed to another role.

**Scratch space** — at `.local/<role>/scratch/`
Free-form, private, never read by others.
Notes, drafts, intermediate analysis, working files.
Can be wiped at any time without consequence.

## Convention

Each agent owns its subdirectory and writes freely there.
Workflow files may be read across roles — scratch may not be relied upon by others.

## What this is not

- Not a substitute for `docs/` — no tracked design decisions here.
- Not a place for committed code or documentation.
- Not shared between machines (gitignored, local only).
