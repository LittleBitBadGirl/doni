# ТСН «ДОНИ» — информационный портал

Веб-портал на FastAPI + HTMX для публикации новостей, финансовой информации, документов, инфраструктурных разделов и контактов ТСН «ДОНИ».

Публичный контент доступен без авторизации. Администрирование — через защищённую панель `/admin`.

## Telegram — двусторонний обмен (два бота)

Портал использует **два отдельных Telegram-бота**. Это разные роли, разные токены, разные направления данных.

| | **Bot 1 — Publish** | **Bot 2 — Inlet** |
| :--- | :--- | :--- |
| **Направление** | Сайт/админка → чат СНТ | Telegram → сайт |
| **Кто пишет** | Автоматически из `/admin` | Члены правления (whitelist) |
| **Куда попадает** | Чат/группа СНТ в Telegram | Раздел **«Важно!»** на сайте (`/news/important`) |
| **Типичный сценарий** | Закрепили новость в админке → бот отправил в чат | Написали боту с телефона → объявление на сайте |

**Сайт — источник истины.** Telegram — каналы доставки и быстрого ввода для правления.

### Схема

```text
[Админка /admin] ──publish-бот──► [Чат СНТ в Telegram]
                                        ▲
                                   собственники читают

[Правление пишет inlet-боту] ──inlet-бот──► [Сайт: /news/important]
```

### Bot 1 — Publish (исходящий)

1. Создайте бота через [@BotFather](https://t.me/BotFather) → сохраните `TELEGRAM_PUBLISH_BOT_TOKEN`.
2. Добавьте бота в **чат СНТ** (группу) и разрешите отправку сообщений.
3. Узнайте `chat_id` группы (через `getUpdates` после сообщения в чат).
4. В `.env`:

```env
TELEGRAM_PUBLISH_ENABLED=true
TELEGRAM_PUBLISH_BOT_TOKEN=123456:ABC...
TELEGRAM_PUBLISH_CHAT_ID=-1001234567890
TELEGRAM_SUBSCRIBE_URL=https://t.me/+invite_link   # опционально, кнопка на сайте
```

**Когда отправляет:**
- новая закреплённая новость из админки — автоматически;
- повторная отправка — чекбокс «Отправить в чат СНТ (publish-бот)»;
- новости, созданные через inlet-бот, **не дублируются** обратно в Telegram.

### Bot 2 — Inlet (входящий)

1. Создайте **второго** бота через @BotFather → `TELEGRAM_INLET_BOT_TOKEN`.
2. Сгенерируйте случайный секрет для webhook, например `openssl rand -hex 32`.
3. Узнайте Telegram ID членов правления: они пишут inlet-боту `/whoami`.
4. В `.env`:

```env
PUBLIC_SITE_URL=https://tsndoni.ru

TELEGRAM_INLET_ENABLED=true
TELEGRAM_INLET_BOT_TOKEN=789012:XYZ...
TELEGRAM_INLET_WEBHOOK_SECRET=ваш-случайный-секрет
TELEGRAM_INLET_ALLOWED_USER_IDS=123456789,987654321
TELEGRAM_INLET_BOT_URL=https://t.me/your_inlet_bot
TELEGRAM_INLET_USE_POLLING=false
```

**Формат сообщения inlet-боту:**

```text
Отключение воды 20 июня
Уважаемые собственники! 20 июня с 10:00 до 14:00
плановое отключение холодной воды.
```

- первая строка → заголовок на сайте;
- остальные строки → текст объявления;
- публикация сразу в раздел **«Важно!»** (`is_pinned=true`).

**Команды inlet-бота:** `/help`, `/whoami`

### Webhook vs polling

| Режим | Когда | Переменная |
| :--- | :--- | :--- |
| **Webhook** | Production (VPS + HTTPS) | `TELEGRAM_INLET_USE_POLLING=false` |
| **Polling** | Локальная разработка без HTTPS | `TELEGRAM_INLET_USE_POLLING=true` |

Webhook URL регистрируется автоматически при старте:

```text
https://tsndoni.ru/api/telegram/inlet/{TELEGRAM_INLET_WEBHOOK_SECRET}
```

Nginx Proxy Manager должен проксировать этот путь на приложение. CSRF для webhook отключён.

### VPS в России

**Да, работает.** Оба бота используют исходящий HTTPS на `api.telegram.org`. Данные сайта (БД, файлы) остаются на VPS в РФ.

| Что уходит в Telegram | Можно |
| :--- | :--- |
| Публичные объявления, заголовки, ссылки | ✅ |
| Списки должников с ФИО, персональные данные | ❌ |

### Проверка end-to-end

**Publish (админка → чат):**
1. В `/admin` создайте новость с «Закрепить на главной».
2. Сообщение появится в чате СНТ.

**Inlet (бот → сайт):**
1. Добавьте свой ID в `TELEGRAM_INLET_ALLOWED_USER_IDS`.
2. Напишите inlet-боту тестовое объявление (формат выше).
3. Откройте `/news/important` — объявление на сайте.

---

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up --build
```

В другом терминале — тестовые данные:

```bash
docker compose exec app python seed.py
```

Откройте http://localhost:8080

| Проверка | URL |
| :--- | :--- |
| Главная | http://localhost:8080/ |
| Важно! | http://localhost:8080/news/important |
| Контакты | http://localhost:8080/contacts |
| Healthcheck | http://localhost:8080/health |
| Админ-логин | http://localhost:8080/admin/login |

**Тестовый админ (после seed):** `admin@tsndoni.ru` / `changeme`

## Локальная разработка (без Docker)

Требуется PostgreSQL 16 локально.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install && npm run build:css

cp .env.example .env
# DATABASE_URL=postgresql+asyncpg://tsndoni:tsndoni@localhost:5432/tsndoni

alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8080
```

Пересборка CSS после правок Tailwind:

```bash
npm run build:css
```

## Стек

- FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Alembic
- Jinja2 + HTMX 2.x + Alpine.js
- Tailwind CSS (CLI build, не CDN)
- SQLAdmin — CRUD для правления
- Telegram Bot API — два бота (publish + inlet), опционально
- Файлы: локальный диск `data/uploads/` (Docker volume)
- Docker Compose: app + postgres + nginx

## Публичные разделы

| Раздел | URL |
| :--- | :--- |
| Главная | `/` |
| Важно! | `/news/important` |
| Новости | `/news`, `/news/{id}` |
| Финансы | `/finance` |
| Документы | `/documents`, `/documents/assembly` |
| Инфраструктура | `/infrastructure/{gas\|water\|electricity\|landscaping}` |
| Контакты | `/contacts` |
| Поиск | `/search` |
| Скачивание файла | `/files/{document_id}` или `/uploads/{path}` |

## Администрирование

1. Вход: `/admin/login` (email + пароль → JWT в HTTPOnly cookie).
2. CRUD: `/admin` — новости, документы, финансы, инфраструктура, контакты.
3. Загрузка файлов (отдельные формы):
   - Документы: `/admin/documents/upload`
   - Список должников: `/admin/finance/debtors/upload`

Контакты редактируются в админке: адрес, телефоны (JSON), URL виджета карты Яндекс.

## Хранение файлов

Документы сохраняются в `data/uploads/{category}/{uuid}.{ext}`.
В Docker — именованный volume `uploads_data`; Nginx раздаёт их по `/uploads/`.
Каталог не попадает в git — для бэкапа копируйте его вместе с дампом БД.

Максимальный размер загрузки: `MAX_UPLOAD_SIZE_MB` (по умолчанию 20).

## Переменные окружения

| Переменная | Описание |
| :--- | :--- |
| `APP_ENV` | `development` или `production` (в prod cookie `Secure`) |
| `SECRET_KEY` | Секрет для JWT и CSRF — сменить в продакшене |
| `DATABASE_URL` | PostgreSQL async URL |
| `UPLOAD_DIR` | Каталог загрузок (по умолчанию `data/uploads`) |
| `MAX_UPLOAD_SIZE_MB` | Лимит размера файла |
| `PUBLIC_SITE_URL` | Публичный URL сайта |
| `TELEGRAM_PUBLISH_ENABLED` | Включить publish-бот (сайт → чат СНТ) |
| `TELEGRAM_PUBLISH_BOT_TOKEN` | Токен publish-бота |
| `TELEGRAM_PUBLISH_CHAT_ID` | ID чата СНТ |
| `TELEGRAM_SUBSCRIBE_URL` | Ссылка на чат СНТ (кнопка на сайте) |
| `TELEGRAM_INLET_ENABLED` | Включить inlet-бот (Telegram → сайт) |
| `TELEGRAM_INLET_BOT_TOKEN` | Токен inlet-бота |
| `TELEGRAM_INLET_WEBHOOK_SECRET` | Секрет webhook URL |
| `TELEGRAM_INLET_ALLOWED_USER_IDS` | Whitelist Telegram user ID через запятую |
| `TELEGRAM_INLET_BOT_URL` | Ссылка на inlet-бота для правления |
| `TELEGRAM_INLET_USE_POLLING` | `true` для dev без HTTPS |
| `YANDEX_METRICA_ID` | ID счётчика Яндекс.Метрики |

Полный список — в `.env.example`.

## Cookie и аналитика

На всех страницах показывается баннер согласия на cookie. Яндекс.Метрика подключается **только после** нажатия «Принять» (или если согласие уже сохранено в `localStorage`).

```env
YANDEX_METRICA_ID=12345678
```

## Деплой на VPS

1. Скопируйте проект на сервер, создайте `.env` с `APP_ENV=production` и надёжным `SECRET_KEY`.
2. Задайте `PUBLIC_SITE_URL=https://ваш-домен.ru` и переменные двух ботов (см. выше).
3. `docker compose up -d --build`
4. `docker compose exec app alembic upgrade head` (если миграции не в entrypoint)
5. `docker compose exec app python seed.py` (только первый запуск)
6. Снаружи — Nginx Proxy Manager для TLS; webhook inlet-бота должен быть доступен по HTTPS.
7. Ежедневный backup: `pg_dump` + архив `data/uploads/` (retention 90 дней).

Healthcheck: `GET /health` → `{"status":"ok"}`.

## Этапы разработки

См. `cursor_project_prompt.md` и `HANDOFF.md` в корневой папке проекта.
