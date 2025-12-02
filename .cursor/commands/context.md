---
description: Quick status check - show project context for resuming work
globs:
---

# Context Command

You are providing a **Quick Context Check**. Your goal is to orient yourself and the user on the current project state.

## Protocol

1. **Read Context File**: Read `CLAUDE.md` if it exists
2. **Check Git Status**: Run git commands to show current state
3. **Summarize**: Present a concise status update

## Steps

### Step 1: Read CLAUDE.md

If `CLAUDE.md` exists, summarize:
- Project overview
- Current focus / active tasks
- Recent context notes

### Step 2: Check Git Status

```bash
# Last 5 commits
git log --oneline -5

# Current changes
git status --short

# Current branch
git branch --show-current
```

### Step 3: Present Summary

Format:
```markdown
## Project Status

**Project**: [Name from CLAUDE.md]
**Branch**: [current branch]
**Current Focus**: [from CLAUDE.md]

### Recent Commits
- [commit summaries]

### Uncommitted Changes
- [file list or "Clean working tree"]

### Recent Notes
- [from CLAUDE.md Recent Context section]

### Suggested Next Steps
- [based on context]
```

## Example Usage

**User**: "/context"

**Response**: 
```
## Project Status

**Project**: dot-claude
**Branch**: update-structure
**Current Focus**: Converting super plugin to Cursor

### Recent Commits
- abc1234 feat: add planning workflow
- def5678 docs: update CLAUDE.md

### Uncommitted Changes
- M .cursor/rules/code-reviewer.mdc
- A docs/cursor-skills/tdd.md

### Recent Notes
- **2025-12-01**: Working on Cursor conversion

### Suggested Next Steps
- Continue with Task 4 of the conversion plan
```

## Workflow Reference

Full workflow: `@.cursor/rules/context-check.mdc`

