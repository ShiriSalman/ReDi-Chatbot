# A limit per visitor

**Project:** ReDI School Chatbot  
**Status:** Specification

## Why

The chatbot runs publicly on Render (since 2026-11-02). Every answered
question uses the owner's free Gemini quota: 15 requests per minute for all
visitors together, plus a daily limit. One visitor, or a script, could use it
up alone. Since `specs/gemini_error_handling.md` ("Iteration: a message for
the used-up quota") a used-up quota gets an honest wait message; this step
keeps a single visitor from causing it.

**Decision (owner, 2026-11-20):** both steps, the quota message first.

## Behaviour

- **At most 5 questions per minute per visitor** (`QUESTIONS_PER_MINUTE`),
  counted over the last 60 seconds (a sliding window).
- **Only questions that reach Gemini count.** Small talk ("thanks"), questions
  the sources don't cover (fallback) and invalid requests don't use the
  quota, so they don't count and are never blocked.
- Above the limit the app answers with **status 429** and `error`: *"You're
  asking very quickly. Please wait a moment and try again."*
  (`VISITOR_LIMIT`), without calling Gemini. The page shows it in the red
  card and puts the question back in the box, like every error.
- `create_app()` gets an optional `rate_limiter`. Without it there is no
  limit: the tests, `tests/test_real_questions.py` and
  `src/run_evaluation.py` (which runs locally) stay unlimited. Only the app
  that gunicorn serves (`app:app`) gets the limit.

## Who is a visitor

The visitor is recognised by their IP address:

- the **first** address in the `X-Forwarded-For` header, if there is one;
- otherwise the address of the connection (`request.remote_addr`).

**Why the first entry:** on Render every request comes through a proxy, so
`remote_addr` would be the same for everyone. Render adds the address it sees
at the end of `X-Forwarded-For` and passes on what the client sent before it
(Render community, checked 2026-11-22). How many proxies (for example
Cloudflare) sit in front isn't documented, so counting from the end could
give a proxy address shared by many visitors, and real visitors would block
each other. The first entry avoids that.

**Trade-off:** a client who sends a fake `X-Forwarded-For` can get around the
limit. That is accepted: the limit is a courtesy limit for a learning
project, not a security barrier, and the quota message still protects the
shared quota.

## Privacy

The addresses are kept only in memory, only for 60 seconds after a visitor's
last counted question, and are never logged or written to a file. Visitors
who were inactive for a minute are forgotten.

## Design

- **`src/rate_limit.py`** (new): `RateLimiter(limit, window_seconds,
  clock=time.monotonic)` with `allow(key)`: True and counted if the key has
  fewer than `limit` calls in the last `window_seconds`, otherwise False. A
  `threading.Lock` protects it, because gunicorn runs 4 threads in one
  worker (`Dockerfile`). The clock is passed in, so tests don't wait.
- **`src/app.py`**: `visitor_key(request)`; in `/api/chat` the model call is
  wrapped, so the limit is checked exactly when Gemini would be called.
- No new dependency (no Flask-Limiter, no Redis).

## Acceptance criteria

`tests/test_rate_limit.py`:
- **AC1:** `allow()` allows `limit` calls in the window and refuses the next.
- **AC2:** after the window has passed, calls are allowed again.
- **AC3:** every key has its own count.
- **AC4:** keys without calls in the last window are forgotten.

`tests/test_app.py`, `TestVisitorLimit`:
- **AC5:** the 6th question within a minute gets 429 and `VISITOR_LIMIT`, and
  Gemini is called only 5 times.
- **AC6:** a minute later the visitor can ask again.
- **AC7:** two visitors (different first `X-Forwarded-For` entries, or
  different connection addresses) have their own limits.
- **AC8:** small talk and fallback questions don't count and aren't blocked.
- **AC9:** without a `rate_limiter`, there is no limit; the served app has a
  limit of 5 per 60 seconds.

By hand (owner, after deploying): asking 6 questions quickly on the live page
shows the message on the 6th; a question from a phone on mobile data still
works at the same time.

## Known limitations

- The count resets when the app restarts (Render's free tier sleeps and
  restarts).
- With more than one gunicorn worker, each worker would count on its own.
- Visitors sharing one address (a school network) share one limit.
- A visitor who changes their address, or fakes the header, gets around it.
