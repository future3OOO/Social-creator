---
name: code-quality
description: Enforce production code quality rules before writing or modifying code. Auto-invoke on any code change to prevent bloat, duplication, cleanup failures, and unnecessary complexity.
disable-model-invocation: false
user-invocable: true
allowed-tools: Read, Grep, Glob
argument-hint: "[file-or-pattern]"
---

# Production Code Quality Gate

Apply these rules to every code change. Violations must be fixed before the change is considered complete.

## 1. Code Volume

- Every line must earn its place. If a fix can make the codebase smaller, it must.
- No wrapper functions for one-time operations.
- No premature abstractions. Three similar lines are better than a premature helper.
- No "just in case" error handling, feature flags, or backwards-compatibility shims.
- If something is unused, delete it completely. No `_unused` renames, no `// removed` comments.

## 2. No Duplication

- If two functions do similar things, consolidate into one.
- Shared operations belong in a single utility file, not scattered across modules.
- Before adding a new function, check if an existing one already covers the need.

## 3. Shortest Path

- Data should flow through the minimum number of steps. Eliminate intermediate hops.
- Every network request, file operation, and function call must be justified.
- If you can eliminate a step without losing functionality, eliminate it.

## 4. Cleanup (Zero Tolerance)

- All temporary files — local and remote — must be cleaned up after every task completes.
- Handle edge cases: abandoned pipelines, partial failures, interrupted flows.
- Cleanup points must exist at: startup, before new work begins, after work completes.
- Leaving orphaned files on a server is a critical failure.

## 5. Anticipate Consequences

- Before making a change, trace its downstream effects across the full stack.
- If changing a limit, constraint, or data shape — update every consumer in the same change.
- If a change could break an existing flow, verify end-to-end before considering it done.
- Never introduce a fix that creates a new problem.

## 6. Simplicity

- Simple problems need simple fixes. Over-engineering is itself a bug.
- No verbose AI-generated patterns: excessive comments, redundant type annotations on obvious code, unnecessary abstractions.
- Production-level means minimal and correct, not enterprise-verbose.

## 7. Python-Specific

- No `# type: ignore` shortcuts. Fix the actual type issue.
- No bare `except:` or `except Exception: pass`. Handle specific exceptions.
- Type hints on all function signatures (args and return types).
- Validate at boundaries only (API responses, external input). Trust internal code.
- No `Any` annotations unless truly unavoidable.

## Review Checklist

When reviewing code (yours or existing), check for `$ARGUMENTS`:

1. **Grep** for `# type: ignore`, bare `except`, `Any` annotations, `TODO`, `FIXME`
2. **Check** for duplicate functions or logic across files
3. **Verify** all temp files have cleanup paths (local and remote)
4. **Confirm** no unnecessary intermediate steps in data flow
5. **Count** lines changed — if the fix grew the codebase significantly, look for what to cut
6. **Trace** the full flow end-to-end to catch downstream breakage
