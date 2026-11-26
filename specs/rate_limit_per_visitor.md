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

> **Changed on 2026-11-26** by "Iteration: the visitor's real address (F2)"
> below: the visitor is now the **third-last** entry. The rest of this
> section is the original decision.

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
- **AC7:** two visitors (different addresses in `X-Forwarded-For`, or
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
- A visitor who changes their address gets around it. (Faking the header no
  longer works since the F2 iteration.)
- The visitor's position in `X-Forwarded-For` depends on Render's proxy chain
  as measured on 2026-11-26. If Render adds more entries, a proxy address may
  be counted and visitors would share a limit (too strict, never a way
  around it); if it adds fewer, the header's first entry is used.

## Iteration: the visitor's real address (F2)

**Status:** done (step 1 diagnosis, step 2 fix).

### Finding (live check, 2026-11-26)

A script sent the same covered question to https://redi-chatbot.onrender.com
twice six times, with a one-minute pause in between:

| Round | Header sent | Result |
|---|---|---|
| A | none | 5 answers, the 6th got `VISITOR_LIMIT` |
| B | a different made-up `X-Forwarded-For` each time (203.0.113.1–6) | 6 answers, no limit |

No reply was Gemini's quota message (`MODEL_BUSY`), so the result is not
caused by the shared quota. Render passes the client's `X-Forwarded-For` on
and adds its own entries after it: the **first entry is chosen by the
visitor**, and the limit can be bypassed with one header. The trade-off above
was accepted on the assumption that this needs effort; it needs none, and one
script can use up the shared quota for every visitor.

The source cited above ("Render community, checked 2026-11-22") can no longer
be checked: the community forum closed on 2026-03-24, and Render's docs don't
describe `X-Forwarded-For`.

### Step 1: find out how many entries Render adds (temporary)

The fix counts from the end of `X-Forwarded-For`, which needs the number of
entries Render's proxies add. That can't be seen from outside, so the served
app logs it for a short time:

- For every question that is counted, one INFO line: the number of
  `X-Forwarded-For` entries, the **names** of other forwarding headers that
  are present (`Forwarded`, `X-Real-IP`, `True-Client-IP`,
  `CF-Connecting-IP`, `CF-Ray`), and, for `X-Real-IP`, `True-Client-IP` and
  `CF-Connecting-IP`, the position in `X-Forwarded-For` whose value equals
  theirs (values are compared, never logged).
- **No address and no header value is logged**, in line with "Privacy" above.
- The owner reads two lines in the Render log: one for a request without the
  header, one with a made-up header. Step 2 removes the log line.

**Acceptance criteria** (`tests/test_app.py`, `TestForwardingLog`):
- **AC10:** a counted question logs the number of `X-Forwarded-For` entries
  and the names of the other forwarding headers present.
- **AC11:** for a client-address header, the line gives the matching
  `X-Forwarded-For` position, or says it matches none.
- **AC12:** the line contains no address and no header value from the request.
- **AC13:** small talk, fallback questions and an app without a
  `rate_limiter` log no such line.

### Measurement (Render log, 2026-11-26, two live questions)

```
X-Forwarded-For has 3 entries; other headers: True-Client-IP, CF-Connecting-IP, CF-Ray; True-Client-IP = entry 1 of 3; CF-Connecting-IP = entry 1 of 3
X-Forwarded-For has 4 entries; other headers: True-Client-IP, CF-Connecting-IP, CF-Ray; True-Client-IP = entry 2 of 4; CF-Connecting-IP = entry 2 of 4
```

The first question sent no header, the second a made-up one. In both, the
real address (the one Cloudflare reports in `True-Client-IP` and
`CF-Connecting-IP`) is the **third-last** entry: Render's proxies add the
visitor's address and two proxy addresses after whatever the visitor sent.

### Step 2: count from the end

**Decision (owner, 2026-11-26):** option A, count from the end of
`X-Forwarded-For`; not `CF-Connecting-IP`, because whether Cloudflare
overwrites one sent by the visitor wasn't checked, and the fix shouldn't
depend on a Cloudflare-specific header.

- `RENDER_PROXY_ENTRIES = 2`: the proxy entries after the visitor's address.
- `visitor_key` uses the entry `RENDER_PROXY_ENTRIES + 1` from the end. With
  fewer entries it uses the first one; without the header,
  `request.remote_addr`, as before.
- The temporary log line of step 1 is removed.

**Acceptance criteria** (`tests/test_app.py`):
- **AC14:** for the two header shapes measured above, the visitor is the
  same address.
- **AC15:** six questions within a minute, each with a different made-up
  first entry but the same real address, get the visitor limit on the 6th.
- **AC16:** visitors with different real addresses have their own limits; a
  header with fewer than three entries uses its first entry; without the
  header the connection address is used.
- **AC17:** the forwarding log line is gone (no counted question logs an
  `X-Forwarded-For` summary).

By hand (after deploying): the live check script from the finding gives the
visitor limit on the 6th question in **both** rounds.
