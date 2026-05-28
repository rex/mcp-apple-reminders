"""Shared test scaffolding for the imperative test scripts at repo root.

Public helpers:
- `TestResults` (from `harness`) — pass/fail/skip accumulator
- `get_current_cst_iso8601` (from `harness`) — timestamp helper for unique test titles
- `cleanup_test_reminders` (from `cleanup`) — delete + verify-deletion helper

Per-domain test modules (`test_crud_*`, `test_workflow_*`) import from here.
"""
