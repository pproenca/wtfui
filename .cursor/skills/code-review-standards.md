# Code Review Standards

## Review Process

Before providing a review, work through these steps explicitly:

### Step 1: Scope Understanding
1. What was the stated goal of this work?
2. What git range am I reviewing? (Verify BASE_SHA and HEAD_SHA)
3. Is there a plan/requirements document to compare against?

### Step 2: Change Mapping
4. Which files were modified, added, or deleted?
5. What is the total line count? (Affects review depth expectations)
6. Run: `git diff --stat {BASE_SHA}..{HEAD_SHA}`

### Step 3: Plan Alignment Check
7. Does every plan requirement have corresponding implementation?
8. Are there implementations without corresponding plan items (scope creep)?
9. Are deviations from plan improvements or problems?

### Step 4: Quality Deep Dive
10. Read each changed file completely
11. Note issues with file:line references
12. Categorize by severity as you go

## Review Dimensions

When reviewing completed work, assess these areas:

### 1. Plan Alignment Analysis
- Compare the implementation against the original planning document or step description
- Identify any deviations from the planned approach, architecture, or requirements
- Assess whether deviations are justified improvements or problematic departures
- Verify that all planned functionality has been implemented

### 2. Code Quality Assessment
- Review code for adherence to established patterns and conventions
- Check for proper error handling, type safety, and defensive programming
- Evaluate code organization, naming conventions, and maintainability
- Assess test coverage and quality of test implementations
- Look for potential security vulnerabilities or performance issues

### 3. Architecture and Design Review
- Ensure the implementation follows SOLID principles and established architectural patterns
- Check for proper separation of concerns and loose coupling
- Verify that the code integrates well with existing systems
- Assess scalability and extensibility considerations

### 4. Documentation and Standards
- Verify that code includes appropriate comments and documentation
- Check that file headers, function documentation, and inline comments are present and accurate
- Ensure adherence to project-specific coding standards and conventions

## Issue Categorization

- **Critical (Must Fix):** Bugs, security issues, data loss risks, broken functionality.
- **Important (Should Fix):** Architecture problems, missing tests, poor error handling.
- **Minor (Suggestions):** Style, optimization, documentation improvements.

## Output Format

```markdown
### Code Review: [Feature Name]

**Summary**: [High level assessment]

**Strengths**:
- [Point 1]
- [Point 2]

**Issues**:
- [Critical/Important/Minor] [File:Line] [Description]

**Verdict**: [Approve / Request Changes]
```

## Handling Incomplete Input

**When plan/requirements missing:**
- Review code against general best practices
- Note: "No plan provided - reviewing against general standards"
- DO NOT assess "requirements met"

**When git range is empty or invalid:**
- Report: "No changes found between BASE_SHA and HEAD_SHA"
- DO NOT produce fabricated review

**When code lacks tests:**
- Flag as Important issue (not Critical unless high-risk)
- Suggest test approaches
- Proceed with quality assessment

**When reviewing generated/vendored code:**
- Note exclusions
- Check for unexpected manual changes
- Focus review on non-generated code

## When to Skip Code Review

**Skip when:**
- Single-line typo fixes or comment corrections
- Dependency version bumps with no code changes
- Documentation-only changes (README, comments)
- Reverting a commit (already reviewed before)
- Auto-generated code updates (migrations, lockfiles)

**Still review even if:**
- "It's just a small change" - small changes can have large impact
- "I'm confident it works" - fresh perspective catches blind spots
- "No tests exist for this area" - review is MORE important here

