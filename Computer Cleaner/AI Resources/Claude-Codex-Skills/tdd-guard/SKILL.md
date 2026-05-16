---
name: tdd-guard
description: Enforce strict test-driven development workflow with red-green-refactor checkpoints.
---

# TDD Guard

## Workflow
1. Write or update a failing test first.
2. Implement the minimal code change needed to pass.
3. Refactor only after tests pass.
4. Re-run focused tests, then broader suite.

## Guardrails
- Never ship behavior changes without tests.
- Keep test scope minimal and deterministic.
- Prefer existing test helpers over new abstractions.
