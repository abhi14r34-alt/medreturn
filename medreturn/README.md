# MedReturn

**Smart mobile medical-waste collection and segregation system**
Smart India Hackathon 2026 — problem statement **SIH26115**

One platform, two connected workflows:

- **Hospital** — AI-assisted biomedical waste identification, routing, quarantine and traceability.
  `Mixed waste → Controlled feed → AI + sensors → Mechanical sort → Quarantine → Logging`
- **Household** — medicine return with pickup scheduling, tracking, verification and credits.
  `Drop → Identify → Lock → Track → Handoff`

---

## Contents

1. [Architecture](#architecture)
2. [Tech stack](#tech-stack)
3. [Folder structure](#folder-structure)
4. [Setup](#setup)
5. [Demo accounts](#demo-accounts)
6. [API reference](#api-reference)
7. [Database schema](#database-schema)
8. [The confidence gate](#the-confidence-gate)
9. [Model training](#model-training)
10. [Demo mode](#demo-mode)
11. [Hardware integration](#hardware-integration)
12. [Security](#security)
13. [Deployment](#deployment)
14. [Limitations](#limitations)
15. [Future work](#future-work)

---

## Architecture

```
┌──────────────┐        ┌─────────────────────────────┐        ┌──────────┐
│  React SPA   │  REST  │        FastAPI API          │  ORM   │  MySQL   │
│  Vite        │ ─────► │  routes → services → models │ ─────► │    8+    │
│  Recharts    │  JWT   │                             │        └──────────┘
└──────────────┘        │  ┌───────────────────────┐  │
                        │  │ ml/inference.py       │  │        ┌──────────┐
                        │  │  real checkpoint      │──┼──────► │ model.pth│
                        │  │  or labelled demo     │  │        └──────────┘
                        │  └──────────┬────────────┘  │
                        │             ▼               │        ┌──────────┐
                        │  ┌───────────────────────┐  │        │ SMTP /   │
                        │  │ ml/decision.py        │  │ ─────► │ maps /   │
                        │  │  the confidence gate  │  │        │ hardware │
                        │  └───────────────────────┘  │        └──────────┘
                        └─────────────────────────────┘         abstractions
```

The ML model never runs in the browser. React posts an image; the backend
preprocesses, infers, applies the gate, writes the record, commands the sorter,
and returns JSON.

**Request flow, end to end:**

```
image → validate → store → preprocess 224×224 → model → confidence
      → decision engine → route or quarantine → DB log → hardware command
      → notification + email → dashboard
```

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18, Vite, React Router, Recharts | Fast dev server, no build config to maintain |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 | Typed request/response, automatic OpenAPI docs |
| Database | MySQL 8+ (PyMySQL) | Specified by the problem statement |
| Auth | JWT (python-jose) + bcrypt (passlib) | Stateless tokens, hashed passwords |
| ML | PyTorch, torchvision, MobileNetV3-Small | Lightweight transfer learning, runs on CPU |
| Email | smtplib behind a service abstraction | Swap for SES/SendGrid without touching callers |

---

## Folder structure

```
medreturn/
├── backend/
│   ├── app/
│   │   ├── core/          config.py, security.py, constants.py
│   │   ├── db/            session.py, init_db.py
│   │   ├── models/        entities.py — 13 tables with foreign keys
│   │   ├── schemas/       Pydantic request/response models
│   │   ├── ml/            inference.py, decision.py
│   │   ├── services/      email, pickups, hardware, maps, storage, ids
│   │   ├── api/
│   │   │   ├── deps.py    auth + role guards
│   │   │   └── routes/    auth, household, hospital, admin, collector, notifications
│   │   └── main.py
│   ├── scripts/           seed_demo.py, create_user.py
│   ├── uploads/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── lib/           api.js, auth.jsx, format.js
│   │   ├── components/    layouts, TopBar, Timeline, FlowDiagram, ui primitives
│   │   ├── pages/         public / household / hospital / admin / collector
│   │   ├── App.jsx        routes + role guards
│   │   └── styles.css     design tokens
│   ├── vite.config.js
│   └── .env.example
├── ml/
│   ├── config.py          CLASSES — single source of truth
│   ├── train.py           transfer learning + best-checkpoint selection
│   ├── evaluate.py        real precision / recall / F1 / confusion matrix
│   ├── predict.py         CLI single-image check
│   ├── preprocessing/     transforms.py, clean.py
│   ├── dataset/           README.md explains the expected layout
│   └── models/            model.pth lands here (gitignored)
├── docs/API.md
├── docker-compose.yml
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.11 or 3.12 (recommended; Python 3.14 on Windows currently fails with the pinned native dependencies)
- Node.js 18 or newer
- MySQL 8 or newer

### 1. Database

```sql
CREATE DATABASE medreturn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'medreturn'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON medreturn.* TO 'medreturn'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Backend

```bash
cd backend

# Recommended: use Python 3.11 or 3.12.
# Avoid Python 3.14 on Windows for this repo until the dependency wheels are available.
py -3.11 -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the environment template and edit it:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

At minimum set `MYSQL_PASSWORD` and generate a real `JWT_SECRET`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create the tables and load demo data:

```bash
python -m app.db.init_db
python -m scripts.seed_demo
```

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: <http://localhost:8000/docs>
Health check: <http://localhost:8000/api/health>

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. In development, Vite proxies `/api` to port 8000,
so no `.env` is needed. For a deployed build, set `VITE_API_URL` to the full API
URL.

### 4. ML (optional — only when you have a dataset)

```bash
pip install torch torchvision
python -m ml.preprocessing.clean --apply
python -m ml.train
python -m ml.evaluate
```

Then point `MODEL_PATH` at the checkpoint, set `DEMO_MODE=false`, and restart
the API.

---

## Demo accounts

Created by `python -m scripts.seed_demo`. Password for all four:
`medreturn123`.

| Username | Role | Sees |
|---|---|---|
| `rhea` | Household | Analyzer, pickups, tracking, credits, history |
| `operator` | Hospital | Waste analyzer, quarantine, traceability, bins, model |
| `admin` | Admin | Everything: pickups, users, hospitals, credits, email log |
| `collector` | Collector | Assigned jobs and the field status buttons |

Registration through the API creates **household accounts only**. Privileged
logins are made deliberately:

```bash
python -m scripts.create_user --role admin --username myadmin \
    --email admin@example.com --name "Your Name"
```

The password is prompted for, never passed as an argument, so it stays out of
shell history.

### A three-minute demo path

1. Sign in as `rhea` → **Medicine Analyzer** → upload any photo → **Request pickup**.
2. Sign in as `admin` → **Pickup Management** → assign a collector, then press
   the green button repeatedly through to **Award credits**.
3. Back as `rhea` → **My Credits**. The balance moved, and the transaction row
   names the pickup that earned it.
4. Sign in as `operator` → **AI Waste Analyzer** → upload a photo. Anything
   under the threshold lands in **Quarantine**, where you release it by hand.

---

## API reference

Full interactive docs at `/docs`. Summary:

### Auth
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | Household accounts only |
| POST | `/api/auth/login` | Returns JWT + user |
| GET | `/api/auth/me` | Current user |
| PATCH | `/api/auth/me` | Update name, phone, address |

### Household
| Method | Path | Notes |
|---|---|---|
| POST | `/api/household/analyze` | multipart image → eligibility + confidence |
| POST | `/api/household/pickups` | Creates `MR-PU-2026-000123` |
| GET | `/api/household/pickups` | Own pickups |
| GET | `/api/household/pickups/{id}` | Detail + status history |
| GET | `/api/household/pickups/{id}/tracking` | Map snapshot, `demo` flagged |
| POST | `/api/household/pickups/{id}/cancel` | Before a collector is on the job |
| GET | `/api/household/credits` | Balance, lifetime, pending |
| GET | `/api/household/credits/transactions` | Ledger |
| GET | `/api/household/history` | Analyzed items |

### Hospital
| Method | Path | Notes |
|---|---|---|
| POST | `/api/hospital/predict` | Image + weight + location → decision |
| GET | `/api/hospital/events` | Traceability search (all filters) |
| GET | `/api/hospital/dashboard` | Totals, averages, daily counts |
| GET | `/api/hospital/bins` | Estimated fill levels |
| GET | `/api/hospital/quarantine` | Held items |
| POST | `/api/hospital/quarantine/{id}/verify` | Human decision, recorded |
| GET | `/api/hospital/model` | Runtime state + version history |

### Admin
| Method | Path | Notes |
|---|---|---|
| GET | `/api/admin/dashboard` | Platform analytics |
| GET | `/api/admin/pickups` | All pickups, filterable |
| PATCH | `/api/admin/pickups/{id}/status` | One stage forward |
| POST | `/api/admin/pickups/{id}/assign` | Assign collector |
| GET | `/api/admin/users` | No addresses in the response |
| GET | `/api/admin/hospitals` · `/collectors` · `/emails` · `/model` · `/settings` | |

### Collector
| Method | Path | Notes |
|---|---|---|
| GET | `/api/collector/pickups` | Assigned jobs |
| PATCH | `/api/collector/pickups/{id}/status` | ON_THE_WAY / ARRIVED / COLLECTED only |
| POST | `/api/collector/pickups/{id}/proof` | Optional collection photo |

### Notifications
`GET /api/notifications` · `GET /api/notifications/unread-count` ·
`PATCH /api/notifications/{id}/read` · `PATCH /api/notifications/read-all`

---

## Database schema

Thirteen tables with foreign keys and timestamps:

`users` · `hospitals` · `waste_events` · `quarantine_events` ·
`household_returns` · `pickup_requests` · `pickup_status_history` ·
`collectors` · `credits` · `credit_transactions` · `notifications` ·
`email_logs` · `model_versions` (plus `sequences`, which backs the readable IDs)

Human-readable identifiers come from a locked counter row, so two concurrent
requests can never take the same number:

- Pickups — `MR-PU-2026-000123`
- Waste events — `MR-WE-2026-000045`
- Quarantine — `MR-QE-2026-00012`

### Pickup lifecycle

```
REQUESTED → SCHEDULED → ASSIGNED → ON_THE_WAY → ARRIVED
          → COLLECTED → VERIFIED → CREDITS_AWARDED → COMPLETED
```

`services/pickups.transition()` is the only function that writes
`pickup_requests.status`. It rejects stage-skipping, writes a history row, sends
the email and creates the notification. `CANCELLED` is reachable from any
non-terminal state.

**Credits are written in exactly one place.** `_award_credits` runs only on the
`CREDITS_AWARDED` transition, which is only reachable after `COLLECTED` and
`VERIFIED` have both been recorded. It checks for an existing transaction and
locks the wallet row, so a pickup cannot be paid twice even if the request is
replayed. Uploading a photo earns nothing.

---

## The confidence gate

`ml/decision.py` — one function, used by both workflows, so the rule cannot
drift apart between them.

```
IF predicted class is in the supported list
AND confidence >= CONFIDENCE_THRESHOLD   (default 0.80, set in .env)
    → ACCEPT  → COMPARTMENT n
ELSE
    → QUARANTINE → human verification
```

Low-confidence items are never routed automatically, whatever the predicted
class. An unsupported class is quarantined even at 99% confidence, because
confidence in a label the system does not handle is not useful.

On the household side the same gate produces `ELIGIBLE`, `NEEDS_REVIEW` or
`UNSUPPORTED`. It reports whether packaging matches an accepted return
category — nothing about whether a medicine is safe, genuine or legal.

---

## Model training

MobileNetV3-Small with ImageNet weights; the classifier head is replaced and
warmed up for three epochs before the backbone unfreezes. EfficientNet-B0 is
available by changing `architecture` in `ml/config.py`.

```
Dataset → cleaning → 70/15/15 split → preprocessing → augmentation
        → transfer learning → per-epoch validation → best checkpoint
        → test evaluation → model.pth
```

The checkpoint stores the class list next to the weights, and the backend reads
the list back from the checkpoint. The API therefore cannot claim a category the
weights do not encode.

`ml/evaluate.py` writes `ml/models/metrics.json` with accuracy, macro and
weighted precision/recall/F1, per-class figures and the confusion matrix. **Those
are the only numbers that belong in a report.** `model_versions` metric columns
are nullable and seeded as `NULL`; the Model Information page says plainly that
no test set has been evaluated rather than displaying a placeholder.

---

## Demo mode

With `DEMO_MODE=true` and no checkpoint at `MODEL_PATH`, the analyzer returns a
result derived from a hash of the image bytes — stable per image, spread across
the confidence range so both sides of the gate get exercised.

It is labelled everywhere it appears:

- API responses carry `inference_mode: "DEMO"` and `is_simulated: true`
- The UI shows a `DEMO MODE` tag on the analyzer and result panels
- Tracking responses carry `demo: true` and the map is marked *Demo tracking*
- Hardware responses carry `hardware_simulated: true`
- Startup logs a warning naming the reason no checkpoint loaded

**With `DEMO_MODE=false` and no loadable checkpoint, inference raises and the API
returns 503.** It does not fall back to invented predictions. An outage is
recoverable; a confident wrong answer about biomedical waste is not.

---

## Hardware integration

```
FastAPI → HardwareController → HTTP/serial bridge → C/C++ firmware → servo gate
```

`services/hardware.py` ships `SimulatedController` (logs the command, returns
`simulated: true`) and `HttpBridgeController` (POSTs to `{HARDWARE_ENDPOINT}/route`).
Set `HARDWARE_ENDPOINT` in `.env` to switch. Nothing in the code or UI claims a
physical gate is connected while the simulator is active.

---

## Security

- Passwords hashed with bcrypt; plaintext is never stored or logged.
- JWT bearer tokens, expiry configurable, verified on every protected route.
- Role guards via FastAPI dependencies (`require_household`, `require_hospital`,
  `require_admin`, `require_collector`).
- Registration cannot create privileged roles.
- Uploads are checked for MIME type, size, and that the bytes actually decode as
  an image; filenames are replaced with a UUID.
- Login returns the same message for an unknown user and a wrong password, so
  the endpoint does not confirm which usernames exist.
- Requesting someone else's pickup returns 404, not 403, for the same reason.
- Household addresses are omitted from `/admin/users` and exposed only to the
  owner, an admin viewing a specific pickup, and the assigned collector.
- Database errors are logged server-side and returned as a generic 503, so SQL
  and connection strings never reach the client.
- All credentials come from environment variables. `.env` is gitignored.

---

## Deployment

**Docker Compose** brings up MySQL, the API and the built frontend:

```bash
cp backend/.env.example backend/.env    # edit first
docker compose up --build
```

Frontend on `:5173`, API on `:8000`, MySQL on `:3306`.

**Manual:** run the API behind gunicorn with uvicorn workers
(`gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`), serve
`frontend/dist` from nginx, and terminate TLS at the proxy. Before going live,
replace `create_all` with Alembic migrations, move uploads to object storage
with signed URLs, and set `CORS_ORIGINS` to your real domain only.

---

## Limitations

Stated plainly, because a prototype that oversells itself is worse than one that
does not:

- **No trained model ships with this repo.** Real accuracy requires a properly
  labelled biomedical waste dataset, which we do not have.
- No performance metrics are reported, because none have been measured.
- GPS tracking is simulated; no maps provider is connected.
- Hardware routing is simulated; no servo or bin sensor is attached.
- Bin fill levels are estimated from logged weights, not read from load cells.
- Email is composed and logged but not delivered until SMTP is configured.
- `create_all` is used instead of migrations; fine for a prototype, not for
  production.
- No rate limiting, and no separate audit log beyond `pickup_status_history`.
- The system makes **no claim** of 100% accuracy, guaranteed safe disposal,
  medical advice, medicine authenticity, regulatory approval, or autonomous
  operation without human checks.

---

## Future work

- Collect and label a real dataset; train, evaluate, publish the confusion matrix.
- WebSockets for live status instead of the current fetch-on-load.
- Alembic migrations and a seeded test suite.
- Real maps provider and live collector GPS.
- Firmware bridge for the sorting gate and load-cell bin sensors.
- OCR pass for expiry dates and batch numbers on packaging.
- The learning loop: verified quarantine decisions become a dataset version for
  a future retraining run — never an automatic update to the deployed model.

---

MIT licensed. See [LICENSE](LICENSE).
