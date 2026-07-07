# Week 2, Day 1 — Celery Fundamentals

**Goal for the day:** understand what a message broker is, what Celery's moving parts are, and why Redis works as a broker — then prove it all works by building a trivial "add two numbers" task completely separate from the real project.

**Definition of done:** call `add.delay(4, 4)` from a Python shell, watch a separate worker process pick it up and execute it, and retrieve `8` back via `result.get()`.

---

## Concepts I had to know (MUST KNOW)

### 1. What a message broker is

In a normal synchronous app (like `live_train_tracker`'s FastAPI routes today), one process does everything — a route handler calls a function directly, in the same call stack, and waits for it to return.

A background job system breaks that apart. One program needs to say "someone should run this task" **without waiting for it to finish, and without a worker even needing to be running at that exact moment.** The "requester" and the "doer" are separate processes that don't talk to each other directly.

A **message broker** is the infrastructure that sits between them: the client drops a message ("run this task with these arguments") into the broker, and the message waits there until a worker is free to pick it up. Like a mailbox — you can drop a letter in even if the recipient isn't home.

**Why this matters for the real project:** background telemetry polling needs to run on a fixed schedule, forever, regardless of whether any user is hitting the API right now. If the FastAPI route called the polling logic directly, that work would only happen when a client requested it, would compete with real request handling for the same process, and a slow/crashed poll could hang or take down user-facing traffic. A broker + separate worker decouples "trigger this work" from "execute this work" into two independent processes on two independent schedules.

### 2. The four Celery pieces and how they hand off to each other

- **Task** — a regular Python function, marked with `@app.task` so Celery knows it's allowed to run asynchronously (it still works as a normal function call too).
- **Client (producer)** — whatever code decides a task should run. Calls `task.delay(...)` (or `.apply_async(...)`), which does **not** run the function immediately — it packages the call into a message, pushes it to the broker, and immediately returns an `AsyncResult` ("claim ticket"), without waiting for the answer.
- **Broker** — Redis, sitting in between, durably holding the queued message until a worker claims it. Doesn't know or care what the task does.
- **Worker** — a separate, long-running process (`celery -A tasks worker`) that continuously polls the broker for new messages, executes the matching function when one arrives, and (if a result backend is configured) stores the return value.

Flow for `add.delay(4, 4)`:
```
Client calls add.delay(4, 4)
  → message pushed to Redis (broker)
  → client gets an AsyncResult back immediately, doesn't block
  → ...independently, whenever a worker is running...
  → Worker polls Redis, finds the message, executes add(4, 4) → 8
  → Worker stores the result (if a result backend is configured)
  → Client calls result.get() later to retrieve 8
```

Client and worker never talk directly — everything passes through Redis. If no worker is running when `.delay()` is called, the message just waits in the queue until one starts and claims it (verified this myself — see "What I did" below).

### 3. Why Redis specifically works as a broker

A broker's core job: reliably hold messages, in order, without losing them, until something consumes them — even if consumers come and go or aren't running yet.

Redis satisfies this because it's a separate, persistent, in-memory process with a **list** data structure that supports push-to-one-end / pop-from-the-other (`LPUSH` / `BRPOP`) — a natural FIFO queue. Celery's `.delay()` is effectively an `LPUSH`; a worker waiting for tasks is effectively blocking on a pop from that list. Being a separate process means a message survives even if the client crashes right after sending it; being in-memory makes push/pop cheap enough for frequent polling.

Caveat noted (not a blocker at this scale): Redis is less durable as a broker than a purpose-built queue like RabbitMQ — if Redis crashes before flushing to disk, unprocessed queued messages could theoretically be lost. Fine for a portfolio project; would matter more at higher stakes.

## Good to know (not load-bearing, parked for later)

- **Result backends** — where a task's return value gets stored so the client can fetch it later. Only needed when you actually care about a task's return value; background jobs that just write to Postgres and return nothing often don't need one at all.

## Skipped for now

- **Celery Canvas** (chains/groups/chords — composing multiple dependent tasks together) — irrelevant until this project has tasks that depend on each other's output.

---

## What I did

1. **Installed and started Redis locally** (already installed via Homebrew on this machine):
   ```bash
   brew services start redis
   redis-cli ping   # → PONG
   ```
2. **Played with Redis's list commands directly**, to see the FIFO queue mechanism Celery relies on with my own hands:
   ```bash
   redis-cli LPUSH mylist "first"
   redis-cli LPUSH mylist "second"
   redis-cli LRANGE mylist 0 -1   # → "second", "first"
   redis-cli RPOP mylist          # → "first" (proves FIFO: first pushed, first out)
   redis-cli DEL mylist
   ```
3. **Set up a standalone toy project**, isolated from the real repo, at `~/Documents/celery-playground/`:
   ```bash
   mkdir celery-playground && cd celery-playground
   python3 -m venv venv
   source venv/bin/activate
   pip install celery redis
   ```
4. **Wrote `tasks.py`**:
   ```python
   from celery import Celery

   app = Celery("tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")

   @app.task
   def add(x, y):
       return x + y
   ```
5. **Ran a worker in one terminal**:
   ```bash
   celery -A tasks worker --loglevel=info
   ```
6. **Acted as the client in a second terminal (Python REPL)**:
   ```python
   from tasks import add
   result = add.delay(4, 4)
   result.get(timeout=5)   # → 8
   ```

## Bug I hit and fixed

First attempt at `result.get()` raised:
```
NotImplementedError: No result backend is configured.
```
Root cause: the `backend="redis://localhost:6379/0"` argument had been dropped when typing the `Celery(...)` line — only `broker=` was present in the file. Fixed by adding `backend=` back in.

This also surfaced an important gotcha: **both the running worker process and the open Python REPL had already imported the old version of `tasks.py` into memory** — editing the file on disk doesn't retroactively change an already-imported module in a live process. Had to restart both the worker and the REPL so they re-read the corrected file from disk. After restarting both, `result.get(timeout=5)` returned `8` as expected.

---

**Status: Day 1 complete.** Next: Day 2 — Redis cache-aside pattern, wired into the real `live_train_tracker` FastAPI routes.
