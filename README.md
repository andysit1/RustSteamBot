# RustSteamBot

A coinflip/trading site for the game Rust, built summer 2023. Players deposit
in-game items via Steam trade offers, get matched against another player, and
a provably-fair flip decides who walks away with both pots (minus a house
cut). This is the **oldest** version of the project — I've since rebuilt it
with different structure, language choices, and design decisions, and I'm no
longer running this codebase. I'm leaving it up and documenting it because
the request/bot-distribution setup is a decent worked example if you're
learning how to fan work out across multiple small servers instead of
scaling one big one.

If you're here to learn, skip to
[**The interesting part: round-robin across DigitalOcean droplets**](#the-interesting-part-round-robin-across-digitalocean-droplets).

## Architecture at a glance

There are two kinds of process in this system, and they never run on the
same machine:

```
                        ┌───────────────────────┐
   Browser  ── HTTP ──▶ │   Web/API server       │
   Browser  ── WS   ──▶ │   (this repo)          │
                        │   FastAPI + WebSockets │
                        └───────────┬────────────┘
                                    │ HTTP (picks one of N)
                       ┌────────────┼────────────┐
                       ▼            ▼             ▼
                 ┌─────────┐  ┌─────────┐   ┌─────────┐
                 │ Bot on  │  │ Bot on  │   │ Bot on  │
                 │Droplet 1│  │Droplet 2│   │Droplet 3│
                 │ (Steam  │  │ (Steam  │   │ (Steam  │
                 │  trade  │  │  trade  │   │  trade  │
                 │  client)│  │  client)│   │  client)│
                 └─────────┘  └─────────┘   └─────────┘
```

- **This repo** is the web app: it serves the site, holds game/room state in
  memory, talks to players over a WebSocket, and persists user records to a
  SQLite database (`app/database.py`, `app/models.py`).
- **The bots** are separate processes (not in this repo) that hold the
  actual Steam sessions and send/accept trade offers. Each one runs its own
  tiny HTTP server (`/trade/{steamid}`, `/user/{steamid}`,
  `/trade_cancel/{roomid}`) that this app calls into.

Splitting it this way exists for one reason: **Steam rate-limits and
sometimes flags accounts that send too many trade offers too fast from one
identity.** One bot process can only safely move so many trades per minute.
So instead of one bot handling every trade on the site, there are three bots
running on three separate DigitalOcean droplets — three different IPs,
three independent request budgets.

## The interesting part: round-robin across DigitalOcean droplets

This is `app/botCalls.py`'s `BotTradeStream` class, and it's the piece of
this project worth actually reading.

### The problem

The web server needs to hand off a trade to *some* bot. If it always asked
the same bot, that bot's IP would take all the traffic (and all the Steam
rate-limit risk) while the other two sat idle — you'd have paid for three
droplets and be running like you only had one.

### The setup

Each droplet is registered by its `ip:port` when the app starts, in a short
one-liner per bot (`app/roomBot.py`). There's also a `loadEnvBots()` path in
`app/botCalls.py` that reads `BOT1`, `BOT2`, ... environment variables
instead of hardcoding IPs in source — the safer way to do this in
production, since it means droplet IPs aren't committed to git.

Internally, the `BotTradeStream` class (`app/botCalls.py`) just keeps two
small dicts: one mapping each bot's IP to a counter of how many times it's
been picked, and one mapping an active room ID to whichever bot IP owns
that room's trade.

### The actual round-robin

The core of it is a single method — `getBestIP()` — and it's a
**least-used** picker, which is a slightly better version of plain
round-robin. Walk through what it does: every bot IP starts at a count of
`0`. Each time a trade needs a bot, it scans all known IPs and returns
whichever one has the *lowest* count so far, then bumps that IP's count by
one. Next call, that IP now has the highest count of the group, so a
different (or the next least-used) IP wins instead.

Concretely, with two bots `A` and `B`, both starting at `0`:

| call | counts before | picked | counts after |
|------|---------------|--------|---------------|
| 1 | A:0, B:0 | A (first seen at the lowest count) | A:1, B:0 |
| 2 | A:1, B:0 | B | A:1, B:1 |
| 3 | A:1, B:1 | A | A:2, B:1 |
| 4 | A:2, B:1 | B | A:2, B:2 |

With equal load per trade, that converges to a straight round-robin split.
The "least-used" framing matters more once trades aren't equal cost — e.g.
if you added weighting or a bot temporarily dropped out, this keeps
balancing toward whichever bot has done the least work, rather than blindly
cycling through a fixed order.

### Pinning a trade to "its" bot

A single trade round-trips (offer sent → player accepts/declines → maybe
cancel), and all of those calls have to hit the **same** bot, because that's
the one holding the actual Steam session for that trade. So the IP is picked
once per room, via `setRoomIP()`, and stored against that room's ID. Every
subsequent call for that room looks up the IP it was pinned to rather than
picking a new bot each time.

`setRoomIP()` is called once, in `roomBot.py`'s `startRoom()`, right when a
room is created — that's the load-balancing decision point. Every later
call for that room (accept, cancel, payout) reuses the pinned IP, so a
trade never gets split across two different Steam sessions mid-flight.

Read-only calls that aren't tied to a specific in-flight trade — like
fetching a Steam profile, which just needs *any* bot to answer — don't
bother with `getBestIP()`'s bookkeeping and just grab a random IP from the
pool instead.

That's the split worth noticing: **stateful, session-bound work gets
sticky/least-loaded routing; stateless reads get plain random routing.**
It's a cheap distinction to make and it's usually the right default when
you're distributing load across independent backend instances that each
hold their own connection/session state.

### What this setup gets you (and what it doesn't)

Gets you:
- Three independent Steam identities, so a rate limit or flag on one bot
  doesn't take down trading for the whole site.
- Trade volume spread roughly evenly across all three droplets with ~10
  lines of code and zero external infrastructure (no load balancer service,
  no service mesh — just an in-process dict).
- Cheap horizontal scaling: adding a fourth bot is one more
  `loadBotManually()` / `BOT4` env var call, no code changes.

Doesn't get you (and this is where I'd improve it if I were doing it again):
- **No health checking.** `getBestIP()` has no idea if a droplet is down —
  it'll happily route trades to a dead bot. A real implementation needs a
  liveness check or a circuit breaker.
- **No persistence.** `roomid_ip` is an in-memory dict. If the web process
  restarts mid-trade, the pinning is lost.
- **In-process only.** This balances load across bots as seen by a *single*
  web server process. It doesn't help if you also scale the web server
  itself to multiple instances — each instance would keep its own counters
  and you could get uneven load again. A shared store (Redis, etc.) would
  fix that.
- Direct-IP routing to droplets also has a downside called out in my own
  notes below: it doesn't hide the backend or give you TLS/retries for
  free. A reverse proxy in front of the bots (or a managed load balancer)
  solves that at the cost of one more moving part.

## Tech stack

- **FastAPI** + **Uvicorn** — HTTP API and ASGI server
- **WebSockets** (via FastAPI) — real-time room/game state pushed to the
  browser (`app/websocketLogic.py`, `app/routers/gamelogic.py`)
- **SQLAlchemy** + **SQLite** — persisted player records (`app/database.py`,
  `app/models.py`)
- **Pydantic** — request/response and in-memory game-state schemas
  (`RoomModel`, `PlayerBet`, `LobbyModel`, `UserData` in `app/models.py`) —
  these are the shared schema between the web server and the trade bots:
  a bot's response payload gets parsed straight into the same models the
  WebSocket layer broadcasts to players.
- **steamio** — Steam client library (used by the bot side, referenced here
  via `steam.Game`/`steam.SteamID`)
- **Docker** — single-container image (see `Dockerfile`), one image deployed
  identically to the web server and (a variant of) each bot droplet

## Running it locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

or with Docker:

```bash
docker build -t ruststeambot .
docker run -p 8000:80 ruststeambot
```

Note this repo only contains the **web server** half of the system. The bot
process that `BotTradeStream` talks to (`/trade/{steamid}`, `/user/{steamid}`,
`/trade_cancel/{roomid}`) isn't included here — without it running somewhere
reachable, trade requests will just fail to connect.

## Lessons learned / what I'd do differently

Notes to myself, left here in case they're useful to you too:

- **Separate the frontend from the backend.** Right now this server serves
  the HTML page directly, which means if the backend crashes, the entire
  site goes down with it. A frontend that only talks to the backend over an
  API (and degrades gracefully if it's unreachable) is much more resilient.
- **Never entangle the WebSocket connection with backend logic.** Keeping
  them separate makes both easier to reason about and to scale
  independently.
- **Validate everything server-side against real game state.** I spent a
  lot of time worried about players hacking the client. The actual fix is
  cheap: if every action is validated against the authoritative game state
  on the server, a manipulated client just can't do anything that wouldn't
  already make sense given where the game actually is.
- **Use a real proxy instead of rotating IPs to get around API limits.**
  The round-robin-across-droplets trick above works, but a dedicated proxy
  service scales better and is less operational overhead than provisioning
  and babysitting more droplets. Worth the cost.
