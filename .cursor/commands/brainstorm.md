---
description: Start brainstorming workflow for idea refinement and design exploration
globs:
---

# Brainstorm Command

You are starting a **Brainstorming Session**. Your goal is to turn a rough idea into a fully-formed design through collaborative questioning, exploration, and incremental validation.

## Protocol

1. **Trigger Workflow**: Immediately reference and follow `.cursor/rules/brainstorming-workflow.mdc`
2. **Announce**: "I'm starting a brainstorming session to refine this idea into a design."
3. **Follow the 4 Phases**: Understanding → Exploring → Presenting → Handoff

## Quick Reference

### Phase 1: Understanding
- Read relevant files/docs to understand existing system
- Ask clarifying questions about scope, constraints, users

### Phase 2: Exploring
- Propose 2-3 approaches with trade-offs
- State your recommendation and why
- Ask user to choose

### Phase 3: Presenting
- Break design into 200-300 word sections
- Validate each section: "Does this look right?"
- Refine based on feedback

### Phase 4: Handoff
- Offer to save design to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Ask if ready to move to implementation planning

## Example Usage

**User**: "/brainstorm I want to add a caching layer"

**Response**: "I'm starting a brainstorming session to refine this idea into a design. First, let me understand the context..."

## What NOT to Do

- Don't start coding immediately
- Don't skip the questioning phase
- Don't present entire design at once
- Don't assume requirements

## Workflow Reference

Full workflow: `@.cursor/rules/brainstorming-workflow.mdc`

