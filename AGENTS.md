# DONI — Project Knowledge Base

For humans and AI agents (Hermes, Cursor, Claude).

---

## What

Информационный портал ТСН «ДОНИ» (Пушкинский район, СПб). FastAPI + Jinja2 + Tailwind + PostgreSQL.

---

## Where

| Ресурс | Адрес |
|--------|-------|
| **Production** | http://91.186.217.66:8765 |
| **Admin panel** | http://91.186.217.66:8765/admin |
| **Health check** | http://91.186.217.66:8765/health |
| **GitHub** | https://github.com/LittleBitBadGirl/doni |
| **Server** | root@91.186.217.66 |
| **SSH key** | ~/.ssh/id_ed25519_deploy |
| **Project path** | /opt/doni (on server) |
| **Local path** | /Users/vera/Desktop/личные_доки/СLI/ДОНИ/tsndoni |

---

## Credentials

| Что | Логин | Пароль |
|-----|-------|--------|
| **Admin panel** | admin@tsndoni.ru | changeme |
| **PostgreSQL db** | tsndoni | doni_secret_2026 |
| **PostgreSQL host** | localhost:5433 | (forwarded from gbrain-pg Docker) |
| **GitHub** | LittleBitBadGirl | stored in Keychain: `security find-internet-password -s github.com -a LittleBitBadGirl -w` |

---

## Deploy

```bash
# First time (done):
#   apt install python3.12-venv
#   git clone https://github.com/LittleBitBadGirl/doni.git /opt/doni
#   cd /opt/doni && python3 -m venv venv
#   ./venv/bin/pip install -r requirements.txt
#   ./venv/bin/alembic upgrade head
#   ./venv/bin/python seed.py

# Update:
ssh -i ~/.ssh/id_ed25519_deploy root@91.186.217.66 '
  cd /opt/doni
  git pull
  ./venv/bin/pip install -r requirements.txt  # if deps changed
  ./venv/bin/alembic upgrade head              # if migrations added
  systemctl restart doni
'

# Check:
curl http://91.186.217.66:8765/health
# → {"status":"ok"}

# Logs:
ssh root@91.186.217.66 'journalctl -u doni -n 50 --no-pager'
```

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI 0.115+ (Python 3.12) |
| Templates | Jinja2 |
| CSS | Tailwind CSS 3 (custom design system) |
| Database | PostgreSQL 17 (asyncpg + SQLAlchemy 2.0 async) |
| Migrations | Alembic |
| Admin | SQLAdmin |
| Auth | JWT (python-jose) + passlib (bcrypt) |
| CSRF | starlette-csrf |
| Rate limit | slowapi |
| Server | uvicorn, systemd |
| Frontend JS | Alpine.js 3 + htmx 2 |
| Fonts | Fraunces + Newsreader (Google Fonts) |

---

## Design System

| Token | Value |
|-------|-------|
| Green | #2d6a4f |
| Green dark | #1b4332 |
| Gold | #c9a227 |
| Sand (bg) | #f4f1de |
| Parchment (cards) | #faf7f0 |
| Bark (text) | #5c4a3d |
| Display font | Fraunces |
| Body font | Newsreader |

CSS: `app/static/css/input.css` → `app/static/css/output.css`
Tailwind config: `tailwind.config.js`

---

## Project Structure

```
/opt/doni/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Pydantic Settings (.env)
│   ├── database.py          # Async SQLAlchemy engine
│   ├── admin.py             # SQLAdmin setup
│   ├── templating.py        # Jinja2 template helpers
│   ├── limiter.py           # Rate limiter
│   ├── dependencies.py      # FastAPI deps
│   ├── auth/                # JWT, cookies, passwords
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # FastAPI route handlers
│   ├── services/            # Business logic (telegram, storage, audit)
│   ├── templates/           # Jinja2 templates
│   └── static/css/          # Tailwind CSS
├── migrations/              # Alembic migrations
├── scripts/preview_ui.py    # Offline HTML preview generator
├── tests/                   # pytest
├── .env                     # Production config
├── requirements.txt
└── seed.py                  # Initial admin user
```

---

## Known Issues / Quirks

1. **bcrypt pinned to 4.0.1** — passlib несовместим с bcrypt 5.x
2. **CSRF на GET** — `/admin/login` убран из `required_urls` (блокировал GET)
3. **app_env=development** на проде — иначе cookie_secure=True ломает логин без HTTPS
4. **Port 5433** — PostgreSQL forwarded через socat из Docker (gbrain-pg:5432 → host:5433)
5. **No domain** — MVP доступен по IP, без SSL

---

## Design Review Status

**Score: B (83/100).** Full report: `docs/design-audit-doni-2026-06-13.md`

Quick Wins (не сделаны):
1. Поменять порядок секций: важные объявления → вверх
2. Поднять body font 14px → 16px
3. Добавить focus-visible
4. Touch-зоны 44px

---

## Local Development

```bash
cd /Users/vera/Desktop/личные_доки/СLI/ДОНИ/tsndoni

# Generate preview files
python3 scripts/preview_ui.py

# Serve preview
python3 -m http.server 8765
# Open http://localhost:8765/preview/index.html

# Run full app locally (needs PostgreSQL)
uvicorn app.main:app --reload --port 8080
```
