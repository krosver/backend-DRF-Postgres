# Система аутентификации и авторизации (DRF + PostgreSQL)

## Описание

Проект реализует собственную систему **аутентификации и авторизации (RBAC)** без использования встроенных auth-механизмов Django.
Цель — показать понимание различий между аутентификацией и авторизацией, JWT-токенами, сессиями и системой разграничения доступа.

---

## Архитектура

### 1. Аутентификация

* Регистрация с валидацией и хэшированием пароля через `bcrypt`.
* Вход по email и паролю с генерацией **JWT access** и **refresh** токенов.
* Создание и хранение **sessionid** в таблице `core.Session`.
* Logout удаляет активную сессию и токен.
* Middleware `core.middleware.AuthMiddleware` автоматически определяет пользователя:

  * из cookie `sessionid`;
  * или из заголовка `Authorization: Bearer <token>`.

Пароли хранятся в виде хэшей. JWT проверяются вручную через `core.auth.parse_jwt`, включая проверку отозванных токенов (`RevokedToken`).

---

### 2. Авторизация (RBAC)

Реализована модель ролей и прав доступа на уровне базы данных.

**Таблицы:**

* `Role` — роль (admin, manager, user)
* `Resource` — код ресурса (`users`, `rbac.rules`, `orders`)
* `PermissionRule` — разрешения роли к ресурсу:

  * `read`, `read_all`, `create`, `update`, `update_all`, `delete`, `delete_all`
* `UserRole` — связь пользователя и роли

**Логика проверки:**

* Проверка доступа через `evaluate_access(user, resource, action, owner_id)`.
* Все роли пользователя объединяются по принципу **OR**.
* Для `read/update/delete` учитываются права на **свои** и **все** объекты.

**Интеграция с DRF:**

```python
class OrderViewSet(...):
    permission_classes = [RBACPermission]
    rbac_resource = "orders"
```

Класс `RBACPermission` автоматически проверяет доступ по действию и роли.

---

### 3. Пользователи

Модель `users.User` — простая, без наследования `AbstractUser`.
Поля: `first_name`, `last_name`, `middle_name`, `email`, `password_hash`, `is_active`, `is_superuser`.
Удаление пользователя — мягкое (`is_active=False`).

**API:**

```
POST   /api/users/register/   — регистрация  
POST   /api/users/login/      — вход  
POST   /api/users/logout/     — выход  
GET    /api/users/me/         — получение профиля  
PUT    /api/users/me/         — обновление данных  
DELETE /api/users/me/         — деактивация пользователя
```

---

### 4. RBAC API

Доступ только администраторам:

```
GET/POST/PUT/DELETE /api/rbac/roles/
GET/POST/PUT/DELETE /api/rbac/resources/
GET/POST/PUT/DELETE /api/rbac/rules/
GET/POST/PUT/DELETE /api/rbac/user-roles/
GET /api/rbac/rules/by_role/?role=manager
```

Инициализация базовых данных через `rbac.fixtures.load()`:

* роли: admin, manager, user
* ресурсы: users, rbac.rules, orders
* права по ролям для демонстрации

---

### 5. Бизнес-модуль

Модуль `biz` содержит фиктивные endpoints для проверки RBAC.
При запросах к ним возвращается либо список данных, либо ошибки `401` (не авторизован) / `403` (нет прав).

---

## Установка и запуск

```bash
git clone <repo_url>
cd <project>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройки БД
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=authpass
export DB_HOST=localhost
export DB_PORT=5433

python manage.py migrate
python manage.py shell -c "from rbac.fixtures import load; load()"
python manage.py runserver
```

---

## Проверка работы

1. Зарегистрируйте пользователя.
2. Через `/api/rbac/user-roles/` назначьте ему роль (`admin`, `manager`, `user`).
3. Проверьте доступ к `/api/biz/...` — RBAC вернёт `403`, если разрешения нет.

---

## Ошибки авторизации

| Код | Описание                  |
| --- | ------------------------- |
| 401 | Пользователь не определён |
| 403 | Доступ к ресурсу запрещён |

---

## Пример схемы ролей

| Роль    | users       | rbac.rules | orders                    |
| ------- | ----------- | ---------- | ------------------------- |
| admin   | все права   | все права  | все права                 |
| manager | read_all    | -          | create/update/read        |
| user    | только свои | -          | read/create/update (свои) |

---

**Технологии:** Django REST Framework, PostgreSQL, bcrypt, JWT
**Python:** 3.10+
