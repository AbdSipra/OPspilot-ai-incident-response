# OpsPilot

> A locally deployed, production-inspired AI incident-response system evaluated using reproducible simulated service failures.

## Overview

OpsPilot is a personal learning and portfolio project that simulates how an AI-assisted incident-response system can investigate application failures safely.

The project will use a small local distributed application with deliberately triggered failures. OpsPilot will receive a monitoring alert, collect observability evidence, retrieve relevant local runbooks, produce an evidence-backed root-cause hypothesis, request human approval for a safe remediation, verify recovery, and generate a postmortem.

OpsPilot is not a production SRE platform and does not connect to real company infrastructure.

## Why this project exists

This project is designed to demonstrate practical understanding of:

- backend development with Python and FastAPI;
- distributed service communication;
- Docker Compose;
- logs, metrics, and distributed traces;
- OpenTelemetry, Prometheus, and Grafana;
- RAG with local runbooks and pgvector;
- LangGraph workflow orchestration and human approval;
- MCP tool boundaries;
- safe AI automation;
- evaluation of AI-assisted incident workflows;
- Git, GitHub, pull requests, and GitHub Actions.

## Current status

The project is in the architecture and repository-setup stage.

- [x] Local Git repository initialized
- [x] GitHub repository connected
- [x] Initial project structure created
- [x] Architecture documentation started
- [ ] Simulated FastAPI services
- [ ] Docker Compose environment
- [ ] Fault injection
- [ ] Observability pipeline
- [ ] OpsPilot investigation workflow
- [ ] RAG runbooks
- [ ] Human approval dashboard
- [ ] Evaluation suite
- [ ] GitHub Actions pipeline

## Planned incident-response flow

```text
Simulated failure
      |
      v
Monitoring alert
      |
      v
Collect logs, metrics, and traces
      |
      v
Correlate evidence across services
      |
      v
Retrieve local runbooks through RAG
      |
      v
Generate structured root-cause hypothesis
      |
      v
Validate safety policy
      |
      v
Human Approve / Edit / Reject
      |
      v
Execute predefined local remediation
      |
      v
Verify service recovery
      |
      v
Generate timeline and postmortem
Planned architecture
Application plane

Synthetic traffic
        |
        v
    edge-api
        |
        v
   orders-api ----------> PostgreSQL application data
        |
        v
  inventory-api

Observability plane

Application services
        |
        v
OpenTelemetry Collector
        |
        +--> metrics store --> Prometheus --> Grafana
        |
        +--> logs and traces --> OpsPilot evidence tools

OpsPilot control plane

Monitoring alert
        |
        v
FastAPI + LangGraph workflow
        |
        +--> PostgreSQL + pgvector runbook search
        |
        +--> MCP tools for evidence collection
        |
        +--> Human approval dashboard
        |
        +--> Safe local fault controller
Simulated application
The demo workload will contain three small FastAPI services.
ServiceResponsibility
edge-apiReceives synthetic user traffic and calls orders-api.
orders-apiProcesses simulated orders, calls inventory-api, and accesses the application database.
inventory-apiSimulates a downstream dependency that can become slow or fail.


This small topology is large enough to demonstrate cross-service failure correlation while remaining understandable and suitable for a normal laptop.
Deliberately triggered failure scenarios
OpsPilot will investigate controlled local failures rather than random or real production incidents.
Failure typeExampleExpected evidenceSafe recovery
API timeoutA downstream service exceeds its caller timeout.Timeout logs, failed spans, rising error rate.Disable the named timeout fault.
Database failureorders-api uses an invalid application database connection configuration.Connection errors, failed database spans, request failures.Restore a known-good local configuration.
Bad configurationA service uses an invalid dependency address, feature setting, or timeout policy.Configuration-version logs and dependency errors.Restore the baseline configuration.
High latencyA service responds successfully but violates a latency objective.Elevated p95 latency and slow trace spans.Disable the named delay fault.


All faults will be injected through a local fault controller with predefined scenarios. The AI will not receive arbitrary Docker, shell, cloud, or database-write access.
Observability
OpsPilot will use three kinds of evidence.
SignalSimple meaningExample use
LogsDetailed event messages.Find a database connection error.
MetricsNumbers measured over time.Detect a rising error rate or p95 latency breach.
TracesThe path of one request across services.Identify the downstream service causing a timeout.


All services will propagate a shared trace ID so OpsPilot can correlate evidence from different services.
AI workflow and RAG
The AI will not be asked to guess from general knowledge alone.
OpsPilot will retrieve relevant local Markdown runbooks through Retrieval-Augmented Generation (RAG). Runbooks will describe:
symptoms;
investigation steps;
evidence to confirm;
safe remediation actions;
rollback guidance;
recovery verification criteria.
The AI output will be validated with a structured schema containing:
severity recommendation;
root-cause hypothesis;
confidence;
evidence references;
runbook references;
one recommended allowlisted action ID.
A diagnosis without valid evidence should be treated as a hypothesis, not a confirmed root cause.
Human approval and safe remediation
OpsPilot will use human-in-the-loop approval before executing any remediation.
The dashboard will support:
Approve: execute the validated recommended action.
Edit: select another permitted action or bounded parameter value.
Reject: record the decision and end without remediation.
The system will execute only typed, predefined demo actions. It will not execute arbitrary commands generated by an LLM.
Every action must pass:
allowlist and policy validation;
human approval;
executor-side validation immediately before execution.
Evaluation plan
The final project will evaluate 15 distinct, versioned simulated incidents:
3 API timeout variants;
4 database failure variants;
4 bad-configuration variants;
4 high-latency variants.
The evaluation will measure:
severity classification accuracy;
root-cause identification accuracy;
evidence citation validity;
runbook retrieval quality;
safe-action acceptance and unsafe-action rejection;
recovery-verification accuracy;
alert-to-diagnosis and action-to-recovery latency;
estimated LLM and embedding cost per incident.
Ground-truth scenario answers will remain outside the AI context and RAG corpus.
Target technology stack
AreaPlanned technology
Backend APIsPython, asynchronous FastAPI, Pydantic
WorkflowLangGraph with persistent state
Database and vectorsPostgreSQL and pgvector
TelemetryOpenTelemetry
Metrics and dashboardsPrometheus and Grafana
Tool interfaceLocal MCP server
User interfaceApproval and incident dashboard
ContainersDocker Compose
Testing and CIPytest and GitHub Actions


Repository structure
apps/          Simulated FastAPI services
opspilot/      Incident workflow, RAG, policies, and MCP server
infra/         Docker, OpenTelemetry, Prometheus, and Grafana configuration
runbooks/      Local Markdown operational runbooks
scenarios/     Controlled fault definitions
evaluations/   Ground truth, results, and evaluation scripts
tests/         Automated tests
docs/          Architecture and design documentation
Git workflow
The project uses short-lived feature branches.
main
  |
  +-- feat/initial-architecture
  +-- feat/demo-services
  +-- feat/fault-injection
  +-- feat/observability
  +-- feat/incident-workflow
  +-- feat/rag-runbooks
  +-- feat/dashboard
  +-- feat/evaluation
  +-- feat/ci
Each feature will follow this workflow:
create branch
  -> make a focused change
  -> run checks
  -> inspect git diff
  -> create a meaningful commit
  -> push branch
  -> open a pull request
  -> merge into main
Scope and limitations
OpsPilot intentionally excludes:
real company infrastructure;
AWS, Kubernetes, PagerDuty, and private production logs;
unrestricted shell or database-write tools;
automated remediation without human approval;
claims of production readiness;
model training.
Portfolio statement
OpsPilot is a locally deployed, production-inspired AI incident-response system evaluated using reproducible simulated service failures.

The project is intended to demonstrate practical AI automation, observability, RAG, backend engineering, Docker, human-in-the-loop workflows, evaluation, and technical judgment.
