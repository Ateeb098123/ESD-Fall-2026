# 🚨 Midnight Launch SRE Game Day Lab
## Enterprise Software Development (ESD) — SRE & Observability Module

Welcome to **The Midnight Ticketmaster Launch Game Day Lab**! In this hands-on lab, you will step into the role of Lead SRE on-call for an API Gateway during a high-stakes global ticket drop. You will run real microservices inside Docker, observe real-time telemetry on Grafana dashboards, inject production chaos using an open-loop Chaos CLI, and write code fixes to protect the system from collapse.

> Design rationale, mathematical models and architecture: `docs/specs/sre-lab-architecture-spec.md`.

---

## 🛠️ Prerequisites & Setup

### 1. Requirements:
- **Docker Engine with the Compose v2 plugin.** Verify with `docker compose version` — it must print a version. The legacy `docker-compose` v1 script is **not** supported (it fails on Python 3.12 with `ModuleNotFoundError: No module named 'distutils'`).
- **Python 3.8+ with the `requests` library** for the Chaos CLI:
  ```bash
  pip install requests
  ```
- Terminal (Bash, Zsh, or PowerShell)
- At least **6 GB of free RAM** and **4 GB of free disk** for the first launch. Elasticsearch, Filebeat, and Kibana are substantially larger than the Python services.

### 2. Launch the Lab Stack:
From inside `labs/week1-midnight-launch/`, run:

```bash
docker compose up -d --build
```

The three Python services declare healthchecks and the gateway waits for its downstreams to become healthy, so your first `/checkout` will not race a half-booted backend.

### 3. Verify Running Services:
Run `docker compose ps`. All 8 containers must be running, and the application services plus Elasticsearch must report **`(healthy)`**:

| Container Name | Service | Port | Description |
| :--- | :--- | :--- | :--- |
| `api-gateway` | Python FastAPI | `http://localhost:8080` | Ingress Gateway with RED metrics, W3C tracing, circuit breaker & fan-out |
| `inventory-service` | Python FastAPI | `http://localhost:8081` | Downstream microservice with DB lock simulation & fan-out dependency |
| `payment-service` | Python FastAPI | `http://localhost:8082` | Third-party mock API with rate limiting |
| `prometheus` | Prometheus TSDB | `http://localhost:9090` | Scrapes telemetry metrics every 1s |
| `grafana` | Grafana Dashboard | `http://localhost:3000` | **Auto-provisioned** SRE War Room Dashboards |
| `elasticsearch` | Elasticsearch 8.15 | `http://localhost:9200` | Stores searchable structured application logs |
| `filebeat` | Filebeat 8.15 | — | Discovers the three labeled application containers and ships their JSON logs |
| `kibana` | Kibana 8.15 | `http://localhost:5601` | Searches and explores the Elasticsearch log indices |

---

## 🔑 Logging into Grafana

1. Open **[http://localhost:3000](http://localhost:3000)**
2. Username **`admin`**, password **`admin`**
3. Grafana may offer a "change password" screen — click **Skip**. The password is pinned to `admin` by `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml`, so changing it is unnecessary for the lab.
4. The dashboard is already provisioned. Jump straight to it:

```
http://localhost:3000/d/sre-war-room
```

Or navigate: **☰ menu → Dashboards → "Midnight Launch — SRE War Room Dashboard"**.

> **Set the time range to `Last 5 minutes` and refresh to `1s`** (top-right controls). The
> dashboard ships with these defaults, but Grafana remembers your last-used values per
> browser, so double-check if panels look empty or frozen.

**If every panel says "Data source not found"** — the Prometheus datasource `uid` did not
provision. Rebuild with `docker compose up -d --force-recreate grafana`.
**If panels are empty but error-free** — that is usually correct: no traffic has been sent
yet. Run `python3 chaos-cli/chaos.py load --rps 50 --duration 20` and watch them fill.

---

## 🌐 Endpoint Reference

Everything below is reachable from your browser once the stack is up, **except `/checkout`**, which is `POST`-only.

### Web UIs — the things you actually open

| URL | Purpose |
| :--- | :--- |
| **`http://localhost:3000/d/sre-war-room`** | **The War Room dashboard.** Metrics, runtime health, outgoing calls, and logs. |
| `http://localhost:9090/targets` | Prometheus scrape targets — fastest way to confirm all 3 services are `UP` and telemetry is flowing. |
| `http://localhost:9090/graph` | Ad-hoc PromQL console with metric-name autocomplete. Good for exploring beyond the dashboard. |
| `http://localhost:9200/_cat/indices?v` | Elasticsearch index inventory; look for `midnight-launch-logs-*`. |
| `http://localhost:5601/app/discover` | Kibana Discover — the primary log exploration UI. |
| `http://localhost:8080/docs` | **Swagger UI for the gateway.** Every chaos endpoint has a **"Try it out"** button — you can drive the whole lab from the browser, no CLI needed. |
| `http://localhost:8081/docs` | Swagger UI — inventory service (DB lock, tail probability). |
| `http://localhost:8082/docs` | Swagger UI — payment service (rate limiting). |

### Service endpoints

| Method | Endpoint | Service | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/checkout` | Gateway :8080 | **The main transaction.** Calls inventory → payment → optional fan-out. Returns the full trace (shared `trace_id`, per-hop `span_id`/`parent_span_id`). Browser `GET` returns **405** — use `curl -X POST` or Swagger. |
| `GET` | `/health` | all three | Liveness. Also drives the Compose healthchecks. |
| `GET` | `/metrics` | all three | Prometheus exposition format — the raw text Prometheus scrapes. |
| `GET` | `/inventory/reserve` | Inventory :8081 | Ticket reservation. Browser-openable: inject `db-lock`, reload, and the tab visibly hangs 3s. |
| `GET` | `/dependency/call` | Inventory :8081 | One fan-out leg. Independently hits its tail with probability `p`. |
| `POST` | `/payment/charge` | Payment :8082 | Charge mock. Sheds `429`s when rate limiting is active. |

### Structured logs in Kibana

Each application request emits one JSON event containing `@timestamp`, `service.name`, `log.level`, HTTP method/path/status, duration, and the shared `trace.id` when available. Filebeat indexes these events into `midnight-launch-logs-YYYY.MM.DD`; Kibana is the log viewer. Grafana remains metrics-only.

On the first launch:

1. Generate at least one event: `curl -X POST http://localhost:8080/checkout`.
2. Open `http://localhost:5601/app/management/kibana/dataViews`.
3. Create a data view named **Midnight Launch Logs** with index pattern `midnight-launch-logs-*`.
4. Select `@timestamp` as the timestamp field.
5. Open **Analytics → Discover** and select **Midnight Launch Logs**.

Use Kibana Query Language searches such as:

```text
service.name:api-gateway
http.response.status_code:[500 TO 599]
trace.id:<paste-a-trace-id-from-checkout>
```

Elasticsearch and Kibana security are disabled only for this isolated classroom stack. Do not expose ports 9200 or 5601 or reuse this configuration in production.

### Chaos control endpoints

All idempotent. The CLI is a thin wrapper — `curl` or Swagger work identically.

| Method | Endpoint | Service | Parameters | Effect |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/chaos/status` | all three | — | **Live chaos state as JSON.** Refresh to watch the breaker change state. |
| `POST` | `/chaos/db-lock` | :8081 | `locked`, `delay` | Inject row-lock latency (Mission 2). |
| `POST` | `/chaos/tail` | :8081 | `probability`, `delay` | Per-dependency tail probability `p` (Mission 4). |
| `POST` | `/chaos/rate-limit` | :8082 | `active`, `error_rate` | Fraction of charges shed as `429` (Mission 3). |
| `POST` | `/chaos/fanout` | :8080 | `n` (0–100) | Parallel dependency count `N` (Mission 4). |
| `POST` | `/chaos/circuit-breaker` | :8080 | `enabled`, `state` | Arm the breaker / force a state (Mission 5). |
| `POST` | `/chaos/cardinality` | :8080 | `active` | Toggle the unbounded `user_id` label (Mission 6). |
| `POST` | `/chaos/reset` | :8080 | — | **Clear everything, including both downstreams.** Your panic button. |

### Handy one-liners

```bash
# Full trace of a single checkout (shared trace_id, distinct span_ids)
curl -s -X POST localhost:8080/checkout | python3 -m json.tool

# What chaos is currently active?
python3 chaos-cli/chaos.py status

# Watch the cardinality bomb inflate the raw metrics
curl -s localhost:8080/metrics | grep -c 'http_requests_user_tagged_total{'

# Reset everything
python3 chaos-cli/chaos.py reset
```

> **Suggested classroom order:** `:9090/targets` (prove telemetry flows) →
> `:3000/d/sre-war-room` (the instrument) → `:8080/docs` (inject chaos) → back to the dashboard.

---

## 🎮 The Open-Loop Chaos CLI (`python3 chaos-cli/chaos.py`)

```bash
# Check current system status & active chaos flags
python3 chaos-cli/chaos.py status

# Open-Loop Traffic Surge (target 300 RPS for 30s, max 20s drain)
python3 chaos-cli/chaos.py load --rps 300 --duration 30 --drain 20

# Inject Postgres Row-Lock delay (3,000ms latency + 15% HTTP 504)
python3 chaos-cli/chaos.py db-lock --delay 3.0
python3 chaos-cli/chaos.py db-lock --off

# Inject Third-Party Payment Rate Limits (40% HTTP 429)
python3 chaos-cli/chaos.py rate-limit --error-rate 0.40
python3 chaos-cli/chaos.py rate-limit --off

# Dean & Barroso Parallel Fan-Out (N=25 dependencies, p=0.01 tail probability)
python3 chaos-cli/chaos.py fanout --n 25 --probability 0.01
python3 chaos-cli/chaos.py fanout --off

# Detonate TSDB Cardinality Bomb (tags user_id in metrics)
python3 chaos-cli/chaos.py cardinality-bomb

# Circuit Breaker (enable CLOSED and let real failures trip it)
python3 chaos-cli/chaos.py circuit-breaker --state CLOSED

# Reset all chaos injections back to baseline normal
python3 chaos-cli/chaos.py reset
```

### 📊 Reading the load generator's output

`load` is **open-loop**: it submits requests on a wall-clock schedule instead of waiting for the previous batch to finish. This matters — a closed-loop generator quietly lowers its own arrival rate when the system slows down, hiding the queueing you are trying to observe.

It reports what it actually achieved:

```
   submitted : 3000 / 3000 scheduled
   completed : 2700  (2700 OK, 300 failed)
   achieved  : 115 RPS vs 300 RPS target (38%)
   ⚠️  System could not absorb the target rate — this is saturation.
```

**A large gap between target and achieved RPS is a finding, not a bug.** It is the system refusing offered load — exactly what Little's Law predicts when $L = \lambda W$ exceeds available concurrency.

> **Realistic ceiling:** ~300 RPS on a typical laptop (measured: 298/300 achieved). Client
> worker threads are capped at 600, so `--rps 10000` will not produce 10,000 RPS — it will
> produce a large target/achieved gap. Use `--rps 300` or lower for clean Little's Law
> demonstrations; treat anything higher as a deliberate saturation experiment.

---

## 🎯 Game Day Incident Missions

### Mission 1: The Midnight Traffic Surge (Little's Law & Kingman's Queueing)
1. Open Grafana at [http://localhost:3000](http://localhost:3000).
2. Run an open-loop surge: `python3 chaos-cli/chaos.py load --rps 300 --duration 30`.
3. **Observe Grafana — Panel 7 (Little's Law):** compare measured `gateway_active_workers` against the predicted $L = \lambda \times W$. As utilization $\rho \to 1.0$, P99 climbs non-linearly (Kingman: $W_q \approx \frac{\rho}{1-\rho}$).
4. **Takeaway:** concurrency is not a setting you choose. Arrival rate times latency imposes it on you.

### Mission 2: The DB Row-Lock Stall (RED vs. USE Lenses)
1. Inject the row-lock: `python3 chaos-cli/chaos.py db-lock --delay 3.0`.
2. Run traffic: `python3 chaos-cli/chaos.py load --rps 50 --duration 20`.
3. **Observe Grafana:**
   - **RED (Gateway):** P99 latency jumps from **~70ms to ~3,000–3,500ms** (measured: 3,495ms — the 3s lock plus the downstream payment call, resolved by the 3.0s/3.5s histogram buckets).
   - **USE (Postgres):** `postgres_connection_pool_waiters` spikes.
   - Error rate also rises: 15% of locked requests return `HTTP 504`.
4. **Takeaway:** the RED metric tells you **THAT** something is slow. The USE metric tells you **WHERE**. You need both — this is the whole argument for the two lenses.
5. Clean up: `python3 chaos-cli/chaos.py db-lock --off`.

### Mission 3: Third-Party Rate Limit Shedding
1. Break the dependency you do not own: `python3 chaos-cli/chaos.py rate-limit --error-rate 0.40`.
2. Run traffic: `python3 chaos-cli/chaos.py load --rps 100 --duration 20`.
3. **Observe Grafana:** the Error Rate % panel climbs to ~40%, driven entirely by `HTTP 429`. Latency stays *fast* — this failure looks nothing like Mission 2 on the Duration panel.
4. **Takeaway:** your error budget can be consumed completely by a service you cannot fix. Compare this panel shape against Mission 2 and note that "checkout is broken" has two totally different signatures.
5. Clean up: `python3 chaos-cli/chaos.py rate-limit --off`.

### Mission 4: Dean & Barroso Parallel Fan-Out Tail Latency
1. Start with a single dependency: `python3 chaos-cli/chaos.py fanout --n 1 --probability 0.01`, then run `load --rps 50 --duration 20`.
2. Raise the fan-out to `--n 10`, then `--n 25`, re-running the load each time. The CLI prints the predicted probability each time you set it.
3. **Observe Grafana — Panel 8:** the observed $P(\text{request slow})$ tracks the predicted curve $P = 1-(1-p)^N$. At $N=25$, $p=0.01$: **~22.2% predicted, 23.0% measured.**
4. **Takeaway:** fan-out turns a rare tail event into the common case. Every dependency is 99% fast, yet nearly 1 request in 4 is slow. **A dependency's P99 becomes the system's P78.**
5. Clean up: `python3 chaos-cli/chaos.py fanout --off`.

### Mission 5: Circuit Breaker Trip & Auto-Recovery
This mission demonstrates the **full state machine**. Do not skip to `--state OPEN`; forcing the state hides the mechanism.

1. Break the payment dependency hard: `python3 chaos-cli/chaos.py rate-limit --error-rate 1.0`.
2. Arm the breaker in its normal state: `python3 chaos-cli/chaos.py circuit-breaker --state CLOSED`.
3. Send traffic: `python3 chaos-cli/chaos.py load --rps 20 --duration 15`.
   After **5 consecutive failures** the breaker trips to **OPEN (1)** and requests fail fast with `HTTP 503` in ~2ms instead of waiting on a doomed downstream call.
4. Heal the dependency: `python3 chaos-cli/chaos.py rate-limit --off`. Wait ~10 seconds.
5. Send traffic again. The breaker admits a probe (**HALF-OPEN (2)**), and after **2 consecutive successes** returns to **CLOSED (0)**.
6. **Takeaway:** a breaker that trips but cannot re-close is just an outage with extra steps. Recovery is half the state machine.

> ⏱ **HALF-OPEN is transient.** Against a healthy backend it lasts only 2 requests, so on a
> 1s-refresh dashboard you will often see `OPEN → CLOSED` and miss the middle state. Watch
> `python3 chaos-cli/chaos.py status` alongside the panel if you want to catch it.

### Mission 6: Detonating the TSDB Cardinality Bomb
1. Trigger the bomb: `python3 chaos-cli/chaos.py cardinality-bomb`.
2. Run traffic: `python3 chaos-cli/chaos.py load --rps 200 --duration 20` (~4,000 requests).
3. **Observe Grafana — Panel 6:** `tsdb_cardinality_series_count` climbs from the baseline **12** by one series for **every distinct `user_id`** — thousands of new series that never existed before. (Measured: 400 requests → 400 distinct series, gauge 412.)
4. **Takeaway:** cardinality is the *product* of distinct label values, $C = N_{metrics} \times \prod V_i$. One unbounded label is enough to exhaust a TSDB's memory. This is precisely why metrics are the wrong tool for per-user debugging — and why traces and wide events exist.
5. Clean up: `python3 chaos-cli/chaos.py reset` (this also frees the leaked label children; the gauge returns to 12).

---

## 💻 Student Coding Exercises

### Exercise 1: Implement Adaptive Load Shedding in `services/api-gateway/app/application.py`
Modify the HTTP middleware to check `ACTIVE_WORKERS`. If active workers exceed 50, return `HTTP 429 Too Many Requests` immediately, before forwarding the request downstream. Then re-run Mission 1 and compare P99 with and without shedding.

### Exercise 2: Fix the Cardinality Bug in `services/api-gateway/app/telemetry.py`
Locate `CARDINALITY_BOMB_COUNTER`. Remove the `user_id` label and replace it with a bounded tag (`user_type="standard"` vs `user_type="vip"`). Re-run `docker compose up -d --build`, repeat Mission 6, and verify the series count stays flat.

---

## 🧹 Teardown

```bash
docker compose down -v
```
