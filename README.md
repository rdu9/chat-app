# chat-app

A realtime chat app, heavily inspired by Discord, where channels are numbered
1–1000. Any logged-in user can read any channel, but only members can post.
Owners approve join requests. Backend built from scratch by me, paired with a
very simple frontend to showcase the app.

**FastAPI · PostgreSQL · Redis pub/sub · WebSockets · Docker · nginx · Cloudflare**

**Live demo:** [https://discord2.xyz](https://discord2.xyz)



---

## What it does

- **Numbered channels.** Pick 1–1000, create one and own it
- **Public read, member write.** Anyone with an account can watch a channel;
posting requires membership
- **Join requests.** Ask to join, and the owner can accept or decline
- **Live messages** over WebSockets, fanned out through Redis pub/sub so
multiple workers stay in sync
- **Emoji reactions** with live counts, toggled by clicking
- **Owners can delete** a channel — messages, memberships and pending requests
cascade away with it



## How it works under the hood

A message posted on one connection is written to Postgres, then published to a
Redis channel. Every WebSocket subscribed to that channel forwards it to its
browser. Redis is what makes this work across more than one worker process —
without it, two users served by different workers would never see each other.

Each socket runs two loops concurrently: one reading from the browser, one
reading from the Redis subscription.

### Authentication

A JWT in an httpOnly cookie, so JavaScript can't read it and it never appears in
a URL or a server log. Cookies go along on the WebSocket handshake, which is how
the socket authenticates — browsers can't set custom headers on a WS connection.

Access tokens last only 15 minutes. A path-scoped refresh cookie buys a new one,
the client retries the failed request once, and the user never notices.

## Running it

```bash
git clone https://github.com/rdu9/chat-app.git
cd chat-app
cp .env.example .env      # fill out all the values
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000) — migrations run
automatically on startup.

### Environment


| Variable                                              | What it is                                                                    |
| ----------------------------------------------------- | ----------------------------------------------------------------------------- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | database credentials                                                          |
| `DATABASE_URL`                                        | `postgresql+asyncpg://user:pass@db:5432/dbname`                               |
| `REDIS_URL`                                           | `redis://redis:6379/0`                                                        |
| `JWT_SECRET_KEY`                                      | generate with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `JWT_ALGORITHM`                                       | `HS256`                                                                       |
| `COOKIE_SECURE`                                       | `false` locally, `true` behind HTTPS                                          |
| `DOMAIN`                                              | hostname the app is served from                                               |


Hostnames are `db` and `redis` — Docker Compose service names, not `localhost`.

## Layout

```
src/
├── auth/        registration, login, cookies, dependencies
├── chat/        channels, messages, reactions, the websocket
├── requests/    join requests
├── db/          db models, engine, redis client
├── static/      the frontend
└── errors.py    every exception the app raises and their status codes
migrations/      alembic config
```



## API


| Method | Path                                  |                               |
| ------ | ------------------------------------- | ----------------------------- |
| POST   | `/api/v1/auth/create`                 | register                      |
| POST   | `/api/v1/auth/login`                  | sets the auth cookies         |
| POST   | `/api/v1/auth/refresh`                | new access token              |
| POST   | `/api/v1/auth/logout`                 | clears them                   |
| GET    | `/api/v1/auth/me`                     | who am I                      |
| POST   | `/api/v1/chat/create`                 | create a channel              |
| DELETE | `/api/v1/chat/{n}`                    | delete it (owner only)        |
| GET    | `/api/v1/chat/mine`                   | channels I'm in or waiting on |
| GET    | `/api/v1/chat/{n}/messages`           | last 50, with reaction counts |
| POST   | `/api/v1/chat/reaction/{message_uid}` | toggle a reaction             |
| WS     | `/api/v1/chat/{n}`                    | live messages and reactions   |
| POST   | `/api/v1/requests`                    | ask to join                   |
| GET    | `/api/v1/requests/{n}`                | pending requests (owner only) |
| POST   | `/api/v1/requests/accept/{uid}`       |                               |
| POST   | `/api/v1/requests/decline/{uid}`      |                               |


Interactive docs at `/docs`.

## Engineering notes

Enconuntered 2 problems worth writing down:

### The stress test

I used a tool that registered 400 accounts in 1 minute against my own site, and It returned 502s and froze everything.

Surprinsingly, the cause wasn't load. bcrypt at cost factor 12 takes ( 400ms ) of CPU per hash and it was running syncronously inside an async def route, so for those 400 ms the event loop couldnt do anything else at all. The db sat at 1% cpu and memory never went above 9%, the process never crashed or restarted it just stopped answering:

```python
hashed = await run_in_threadpool(generate_passwd_hash, payload.password)
```

the app now just degrades instead of freezing, because the host has only one core, and its not meant for load.

### The problem moves, not dissapears

The fix lead to another separate failure:

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached
```

With the loop now unblocked, hundreds of registrations ran at the same time, each holding a database session across its own 400ms hash.

The interesting part is that it was actually *worse* here: with only one core, 30 hashes finish no sooner than 30 sequential ones, but each holds a connection 30 times longer.

## Known limitations
  
- **No rate limiting implemented yet.**.
- **No tests.** Every bug in this project was found by clicking.
- **No indexes** beyond primary keys and constraints.
- **Refresh tokens aren't rotated or revocable.** 
- **No backups.** Hosted on one digitalocean droplet, one volume.
- **No monitoring.** Nothing alerts me when it's down.


NOTE: The frontend is deliberately minimal: one HTML file. This is a backend project, and the UI exists just to showcase the API.
