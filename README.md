# OpenPage Backend

Инструкция по скачиванию проекта с GitHub и запуску на другом устройстве без лишних проблем.

## Что понадобится

- `Git`
- `Docker Desktop` или `Docker Engine` + `Docker Compose`

Рекомендуется проверить заранее:

```bash
git --version
docker --version
docker compose version
```

## 1. Скачать проект с GitHub

Откройте терминал и выполните:

```bash
git clone <ССЫЛКА_НА_РЕПОЗИТОРИЙ>
cd OpenPage-Backend
```

Если репозиторий приватный, сначала авторизуйтесь в GitHub удобным для вас способом.

## 2. Подготовить файл окружения

В корне проекта должен быть файл `.env`.

Если он уже есть в репозитории, проверьте значения внутри.
Если его нет, создайте вручную файл `.env` и заполните примерно так:

```env
DEBUG=True
DB_NAME=openpage
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
USE_REDIS=False
API_SECRET_KEY=your_secret_key_here

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin123
DJANGO_SUPERUSER_EMAIL=admin@example.com

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@example.com

TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_URL=
TELEGRAM_BOT_USERNAME=
```

Важно:

- не используйте чужие токены, пароли и ключи
- на другом устройстве лучше сгенерировать новый `API_SECRET_KEY`
- если Telegram и email сейчас не нужны, можно временно оставить их пустыми или подставить свои значения

## 3. Запустить проект

В корне проекта выполните:

```bash
docker compose up --build
```

При первом запуске контейнер автоматически:

- соберет образ
- поднимет PostgreSQL
- поднимет Redis
- применит миграции
- соберет статику
- создаст суперпользователя, если его еще нет
- запустит Django-сервер

## 4. Проверить, что все работает

После запуска должны быть доступны:

- API: `http://localhost:8000/`
- Swagger: `http://localhost:8000/api/docs/`
- Schema: `http://localhost:8000/api/schema/`
- Admin: `http://localhost:8000/admin/`

Для входа в админку используйте:

- логин: значение `DJANGO_SUPERUSER_USERNAME`
- пароль: значение `DJANGO_SUPERUSER_PASSWORD`

## 5. Остановить проект

```bash
docker compose down
```

Если нужно остановить проект и удалить тома базы/redis:

```bash
docker compose down -v
```

Внимание: `-v` удалит данные контейнеров.

## 6. Повторный запуск

Если проект уже был собран раньше:

```bash
docker compose up
```

Если менялись зависимости, Dockerfile или важные настройки:

```bash
docker compose up --build
```

## 7. Полезные команды

Посмотреть логи:

```bash
docker compose logs -f
```

Посмотреть только backend:

```bash
docker compose logs -f web
```

Запустить миграции вручную:

```bash
docker compose exec web python manage.py migrate
```

Создать нового суперпользователя вручную:

```bash
docker compose exec web python manage.py createsuperuser
```

## Частые проблемы

### Порт 8000 занят

Если `8000` уже используется другим приложением, измените проброс порта в `docker-compose.yml`:

```yml
ports:
  - "8001:8000"
```

Тогда проект будет доступен по адресу:

`http://localhost:8001/`

### Порт PostgreSQL 5434 занят

В проекте база проброшена как `5434:5432`.
Если порт `5434` занят, измените его в `docker-compose.yml`.

### Docker не запущен

Если видите ошибки вида `failed to connect to the docker API`, просто запустите Docker Desktop и дождитесь, пока он полностью поднимется.

### Проблемы после обновления кода

Выполните:

```bash
docker compose down
docker compose up --build
```

### Нужно полностью пересобрать проект с нуля

```bash
docker compose down -v
docker compose up --build
```

## Обновление проекта с GitHub

Если проект уже скачан и нужно получить последние изменения:

```bash
git pull
docker compose up --build
```

## Короткий сценарий запуска

Если совсем кратко:

```bash
git clone <ССЫЛКА_НА_РЕПОЗИТОРИЙ>
cd OpenPage-Backend
docker compose up --build
```

Если понадобится, я могу следующим сообщением еще дописать отдельный блок для запуска без Docker через локальный Python.
