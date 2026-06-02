# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Repository Purpose

This is a workshop sample repo — a simple Pong game used to demonstrate
end-to-end agentic coding workflows. The codebase is intentionally simple.

## Workflow Rules

- Always work on a feature branch, never commit directly to main
- Always open the game in a browser and verify it loads without errors before committing
- Never modify index.html or style.css unless explicitly asked
- Keep all game logic in game.js — do not split into multiple files
- When raising a PR, write a verbose description covering: what changed, why,
  and the technical approach taken
- Before implementing any feature, ensure a spec or plan has been discussed and agreed

## Destructive Action Rules (Strict)

- NEVER force push to any branch (`git push --force` is forbidden)
- NEVER run `git reset --hard` or `git clean -f` without explicit user confirmation
- NEVER delete any file — if a file needs replacing, overwrite it in place
- NEVER drop or truncate game.js — always make targeted edits, never rewrite the whole file from scratch
- NEVER delete local or remote branches without explicit user instruction
- NEVER modify .gitignore in a way that could expose .claude/notes-config.json or other private config
- NEVER run destructive shell commands (rm -rf, truncate, dd) under any circumstances
- If unsure whether an action is destructive, STOP and ask the user before proceeding

## Skills Available

The following skills are available in `.claude/skills/`:

| Skill | Trigger | Purpose |
|-------|---------|---------|
| e2e-workflow | `/e2e-workflow [feature idea]` | Full pipeline: brainstorm → grill-me → plan → build → review → doc-review → PR |
| brainstorming | "brainstorm [feature]" | Structured design with HTML visualiser |
| grill-me | `/grill-me` | Stress-test a plan or spec |
| doc-review | `/doc-review` | Update docs after architectural changes |
| using-superpowers | "what skills are available?" | Overview of all skills |
