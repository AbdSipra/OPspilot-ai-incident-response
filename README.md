# OpsPilot

A locally deployed, production-inspired AI incident-response system evaluated using reproducible simulated service failures.

## Status

Work in progress.

## Core idea

OpsPilot receives a simulated alert, collects logs, metrics and traces, searches local runbooks, proposes an evidence-backed remediation, pauses for human approval, executes only a predefined safe action, verifies recovery, and creates a postmortem.
