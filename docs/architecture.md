# OpsPilot Architecture

## 1. Purpose

OpsPilot is a locally deployed, production-inspired AI incident-response system. It investigates deliberately simulated failures and helps a human choose a safe recovery action.

## 2. Project boundary

- The project runs only on your local laptop.
- It uses synthetic services, logs, metrics, traces, and runbooks.
- It does not connect to real company infrastructure, cloud accounts, customer data, or production systems.

## 3. Simulated application

The demo application will contain three small FastAPI services:

- edge-api: receives synthetic user requests and calls orders-api.
- orders-api: processes a simulated order, calls inventory-api, and uses the application database.
- inventory-api: simulates a downstream dependency that can become slow or fail.

PostgreSQL will store simulated application data.

## 4. Normal request flow

```text
Synthetic user traffic
        |
        v
    edge-api
        |
        v
   orders-api ----------> PostgreSQL
        |
        v
  inventory-api
A downstream service is a service that another service calls.
In this project, inventory-api is downstream from orders-api, and orders-api is downstream from edge-api.

## 5. Simulated failure scenarios

OpsPilot will investigate deliberately triggered local failures.

### API timeout

A service takes longer than its caller's timeout limit.

Example: orders-api waits too long for inventory-api, then edge-api returns an error to the synthetic user.

### Database failure

orders-api cannot use the simulated application database.

Example: a deliberately invalid connection configuration causes database connection errors.

### Bad configuration

A service uses an incorrect but controlled configuration value.

Example: edge-api receives an invalid downstream service address or timeout setting.

### High latency

A service still responds successfully but becomes slower than the acceptable service-level objective.

Example: inventory-api adds an artificial delay, causing high p95 response latency.

Each failure will be triggered through a local fault controller. The fault controller will expose only predefined demo scenarios and safe recovery actions.

## 6. Observability

Observability helps us understand what happened inside a distributed system.

### Logs

Logs are detailed event records.

Example: orders-api records that a database connection failed, including the service name, time, error type, and trace ID.

### Metrics

Metrics are numeric measurements collected over time.

Examples:

- request count;
- error rate;
- request duration;
- p95 latency;
- database connection failure count.

Prometheus will collect metrics, and Grafana will display them in dashboards.

### Traces

Traces show the path of one request across services.

Example:

```text
edge-api -> orders-api -> inventory-api
If inventory-api is slow, the trace can show that orders-api waited for it and edge-api eventually returned a timeout.
Correlation
All services will propagate a trace ID.
The trace ID lets OpsPilot connect a log message, metric spike, and distributed trace to the same incident investigation.
Services -> OpenTelemetry Collector -> telemetry stores -> Grafana and OpsPilot

## 7. Incident workflow

An alert tells OpsPilot that a monitored service may be unhealthy.

Examples of alert conditions:

- error rate is above an allowed threshold;
- p95 latency is above an allowed threshold;
- database connection failures are detected.

OpsPilot will follow this workflow:

```text
1. Receive alert.
2. Create an incident record.
3. Collect relevant logs, metrics, and traces.
4. Correlate evidence across services.
5. Search local runbooks through RAG.
6. Produce an evidence-backed root-cause hypothesis.
7. Propose one safe remediation action.
8. Pause for human approval, edit, or rejection.
9. Execute an approved allowlisted action.
10. Verify whether the service recovered.
11. Create an incident timeline and postmortem.
LangGraph will manage the workflow state.
Workflow state means the saved information about the current incident, such as the alert, evidence references, diagnosis, approval decision, action result, and recovery result.
The workflow must be persistent so that it can pause at human approval and resume later without losing incident information.
