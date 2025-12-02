---
description: Add session notes to CLAUDE.md for future context
globs:
---

# Notes Command

You are adding **Session Notes** to CLAUDE.md. This creates a "session memory" pattern for resuming work later.

## Protocol

1. **Ask User**: "What should we note about this session?" (if not provided)
2. **Read CLAUDE.md**: Get current content
3. **Update**: Add timestamped entry to Recent Context section
4. **Confirm**: Report that note was added

## Steps

### Step 1: Get Note Content

If user didn't provide the note, ask:
> "What would you like to note about this session?"

### Step 2: Read CLAUDE.md

Read the current content of `CLAUDE.md`.

### Step 3: Update Recent Context Section

Find or create the "Recent Context" section under "Current Focus".

Add entry format:
```markdown
### Recent Context
- **YYYY-MM-DD**: [user's note here]
- **YYYY-MM-DD**: [previous note]
```

**Rules:**
- Add new entry at the top
- Keep only the last 5 entries to avoid bloat
- Use today's date

### Step 4: Confirm

Report: "Note added to CLAUDE.md: '[abbreviated note]'"

## Example Usage

**User**: "/notes Finished converting skills to docs/cursor-skills"

**Response**:
1. Read CLAUDE.md
2. Add entry: `- **2025-12-01**: Finished converting skills to docs/cursor-skills`
3. Confirm: "Note added to CLAUDE.md."

**User**: "/notes"

**Response**: "What would you like to note about this session?"

## Format Example

Before:
```markdown
### Recent Context
- **2025-11-30**: Started plugin consolidation
- **2025-11-29**: Fixed test failures
```

After adding note "Completed Cursor conversion":
```markdown
### Recent Context
- **2025-12-01**: Completed Cursor conversion
- **2025-11-30**: Started plugin consolidation
- **2025-11-29**: Fixed test failures
```

## Workflow Reference

Full workflow: `@.cursor/rules/session-notes.mdc`

