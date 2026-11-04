---
name: std-dev
description: Standard data-type-driven development flow — optional live-API probe, plan the data flow and validation schemas before writing logic, type-first implementation, run the test suite, then commit and push. Use when starting feature development, bug fixes, or any non-trivial code change. No design documents or diagram files are written.
---

# std-dev — Standard Development Flow

The standard way to build and change code. Core principle: **design the data
flow first, make types the single source of truth, then implement type-first.**
No design documents or diagram files are written — the plan lives in the
conversation (or plan mode), and the validation schemas in the code are the
durable artifact.

This skill defines the flow only. Project-specific tools, paths, commands, and
issue-tracker conventions live in the project's agent instructions (e.g.
AGENTS.md).

## The Flow

### 1. Integration probe (optional)

Only when the task touches an external API whose real response shape is unknown
or uncertain. Write a probe that hits the live service (no mocking) and keep the
real response shapes for steps 2–3. Skip when shapes are already known (existing
schemas, prior probes, docs). Follow the project's probe conventions (location,
run command, secrets handling, self-contained tests).

### 2. Plan the data flow

Before touching implementation code, map how data moves through the change:

- **Boundaries** — every external input entering scope: API responses,
  environment variables, request bodies, form input, query params, JSON parses
- **Data structures** — each distinct shape crossing a module boundary gets
  exactly one canonical schema; producer and consumer both import it
- **Transformation path** — producers → validation points → consumers; validate
  once at subsystem entry, trust downstream
- **Constraints** — invariants the change must honor (user stories,
  nonfunctional requirements); each traces to ≥1 structure or check

Use probe data from step 1 as the source of truth for shapes. For non-trivial
work, enter plan mode and get user approval of this plan before coding; a bug
fix starts from reproducing the bug, then tracing its data path.

### 3. Define validation schemas first (core step)

Write the schemas identified in step 2 before any business logic, following the
project's type-driven design rules:

- Schema first, type inferred — never a parallel hand-written type
- Parse at boundaries — hard-fail where invalid data must abort; graceful parse
  only for user-facing errors. Trust validated data internally
- Make invalid states unrepresentable — constrain in the schema rather than
  ad-hoc checks downstream
- Shared structures defined once in a canonical location
- Validation failures name the data structure and the offending field

Full discipline: [references/type-driven.md](references/type-driven.md).

### 4. Implement type-first

Incremental, driven by the schemas: types → core logic → wiring. Apply the High
Cohesion & Low Coupling principles below, plus the project's architecture rules.
Keep the change scoped to the task; fix root causes, never paper over symptoms.

### 5. Test

Run the project's quality gate: the unit test suite plus format, lint, and type
checks, all clean before proceeding. Add unit tests for new logic in the
project's test locations, mirroring source structure. Frontend/UI verification
only when the user explicitly asks for it.

### 6. Commit and push

Follow the project's git conventions: conventional commits describing the why,
issue references without auto-closing keywords, comments on issues left for a
human to close. Push once the quality gate passes.

## High Cohesion & Low Coupling

Non-negotiable design requirements throughout the flow:

- **Single responsibility:** Each module, component, and function should do one
  thing and do it well. If it must change for multiple unrelated reasons, split
  it.
- **Minimize dependencies:** Prefer passing data through explicit parameters
  over shared mutable state or global singletons. A change in one module should
  not cascade to others.
- **Encapsulate boundaries:** Modules communicate through well-defined
  interfaces (typed params and return values), never through internal
  implementation details.
- **Extract, don't duplicate:** When two places share logic, extract it into a
  focused shared helper rather than copy-pasting. But avoid premature
  abstraction — three similar lines is fine.
- **Dependency direction:** Dependencies flow inward — UI, routes, and entry
  points depend on shared core logic; core logic never depends on them.

Project-specific elaborations (e.g., component isolation rules) live in the
project's agent instructions.

## Resources

- [references/type-driven.md](references/type-driven.md) — "Parse, don't
  validate" implementation discipline for steps 3–4
