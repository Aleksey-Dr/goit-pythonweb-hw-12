<a id="top"></a>

<a href="#1"><img src="https://img.shields.io/badge/Создание и подключение к базе данных-512BD4?style=for-the-badge"/></a> <a href="#2"><img src="https://img.shields.io/badge/Запустить API-ECD53F?style=for-the-badge"/></a> <a href="#3"><img src="https://img.shields.io/badge/Обзор функциональности API-007054?style=for-the-badge"/></a> <a href="#4"><img src="https://img.shields.io/badge/Пакеты-A9225C?style=for-the-badge"/></a> <a href="#5"><img src="https://img.shields.io/badge/Файл .env-583E26?style=for-the-badge"/></a>
<a href="#6"><img src="https://img.shields.io/badge/Примечания-A78B71?style=for-the-badge"/></a> <a href="#7"><img src="https://img.shields.io/badge/Ошибки-EC9704?style=for-the-badge"/></a> <a href="#8"><img src="https://img.shields.io/badge/Docstrings-9C4A1A?style=for-the-badge"/></a>

<a id="1"></a>

#### <img src="https://img.shields.io/badge/1. Создание и подключение к базе данных-512BD4?style=for-the-badge"/>
В этой работе мы будем использовать базу данных postgres.

Убедитесь, что у вас запущен сервер PostgreSQL и указана база данных в созданном файле `.env`.

В командной строке запустите контейнер Docker:

```bash
docker run --name some-postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword -d postgres
```
Вместо `some-postgres` выберите имя вашего контейнера, а вместо `mysecretpassword` придумайте свой пароль для подключения к базе данных.

SQLAlchemy автоматически создаст таблицу `contacts` при первом запуске API благодаря строке в файле `main.py`:
```python
database.Base.metadata.create_all(bind=database.engine)
```
**Создание базы данных «контакты» в PostgreSQL:**
1. Перейдите в Docker-контейнер PostgreSQL:
```bash
docker exec -it contacts bash
```
2. Переключитесь на пользователя `name`, например, `postgres`:
```bash
su postgres
```
3. Запустите клиент `psql`:
```bash
psql
```
>[!Note]
>Вы должны увидеть командную строку. `postgres=#`.
4. Создайте базу данных «контактов»:
```sql
CREATE DATABASE contacts;
```
5. Проверьте список существующих баз данных:
```sql
\l
```
6. Выйдите из `psql` и контейнера:
```sql
\q
exit
exit
```

[Вверх :arrow_double_up:](#top)

<a id="2"></a>

#### <img src="https://img.shields.io/badge/2. Запустить API-ECD53F?style=for-the-badge"/>
Убедитесь, что вы находитесь в корневом каталоге проекта (где находится файл `main.py`) и запустите API с помощью Uvicorn:
```
uvicorn main:app --reload
```
После запуска вы сможете получить доступ к документации Swagger по адресу `http://127.0.0.1:8000/docs` или `http://127.0.0.1:8000/redoc`.

[Вверх :arrow_double_up:](#top)

<a id="3"></a>

#### <img src="https://img.shields.io/badge/3. Обзор функциональности API-007054?style=for-the-badge"/>
1. POST /contacts/: Создать новый контакт. Ожидает тело запроса JSON с данными контакта.
*Пример curl-запроса:*
```bash
 curl -X POST -H "Authorization: Bearer <ваш_access_token>" -H "Content-Type: application/json" -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "123-456-7890",
    "birthday": "1990-01-15",
    "additional_data": "Some additional info"
}' http://localhost:8000/contacts
```
2. GET /contacts/: Получить список всех контактов. Поддерживает разбиение на страницы с использованием параметров `skip` и `limit`, а также фильтрацию по `first_name`, `last_name` и `email` через параметры запроса.
*Примеры curl-запросов:*
    - Получить все контакты:
    ```bash
    curl -X GET -H "Authorization: Bearer <ваш_действующий_access_token>" http://localhost:8000/contacts
    ```
    - Получить вторую страницу (пропустить первые 10, лимит 20):
    ```bash
    curlcurl -X GET -H "Authorization: Bearer <ваш_действующий_access_token>" http://127.0.0.1:8000/contacts/?skip=10&limit=20
    ```
    - Получить контакты с именем "Ivan":
    ```bash
    curl -X GET -H "Authorization: Bearer <ваш_действующий_access_token>" http://127.0.0.1:8000/contacts/?first_name=Ivan
    ```
    - Получить контакты с фамилией "Petrov" на первой странице (лимит 10):
    ```bash
    curl -X GET -H "Authorization: Bearer <ваш_действующий_access_token>" http://127.0.0.1:8000/contacts/?last_name=Petrov&limit=10
    ```
3. GET /contacts/{contact_id}: Получить отдельный контакт по его идентификатору (ID).
*Пример curl-запроса:*
```bash
curl -X GET -H "Authorization: Bearer <ваш_действующий_access_token>" http://127.0.0.1:8000/contacts/123
```
4. PUT /contacts/{contact_id}: Обновить существующий контакт по его идентификатору (ID). Ожидает тело запроса JSON с обновленными данными.
*Пример curl-запроса:*
```bash
curl -X POST -H "Authorization: Bearer <ваш_access_token>" -H "Content-Type: application/json" -d '{"first_name": "Piter", "phone_number": "+380509876543"}' http://127.0.0.1:8000/contacts/123
```
5. DELETE /contacts/{contact_id}: Удалить контакт по его идентификатору(ID).
*Пример curl-запроса:*
```bash
curl -X DELETE -H "Authorization: Bearer <ваш_действующий_access_token>" http://127.0.0.1:8000/contacts/123
```
6. GET /contacts/birthdays/upcoming: Получите список контактов, у которых день рождения в ближайшие 7 дней.
*Пример curl-запроса:*
```bash
curl -X GET -H "Authorization: Bearer <ваш_действующий_access_token>" http://127.0.0.1:8000/contacts/birthdays/upcoming
```

>[!Tip]
>Функция get_upcoming_birthdays корректно обрабатывает дни рождения, выпадающие на 29 февраля, даже в невисокосные годы, рассматривая их как 28 февраля для целей определения предстоящих дней рождения в течение следующей недели.

7. **Регистрация нового пользователя (успешный случай):**
*Пример curl-запроса:*
```bash
curl -X POST -H "Content-Type: application/json" -d '{
    "email": "newuser@example.com",
    "password": "securePassword123",
    "username": "new_user"
}' http://localhost:8000/register
```
Ожидаемый успешный ответ: HTTP-статус `201 Created` и JSON с данными нового пользователя, например:
```bash
{"id":2,"username":"new_user_1","email":"newuser_1@example.com","is_active":true
,"is_verified":false,"created_at":"2025-04-23T12:31:47.738836","avatar_url":null
}
```
8. Регистрация пользователя, который уже существует (ошибка 409 Conflict):
Ожидаемый ответ: HTTP-статус `409 Conflict` и JSON с сообщением об ошибке.
9. Аутентификация пользователя (успешный вход):
*Пример curl-запроса:*
```bash
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "username=<email>&password=<password>" http://localhost:8000/login
```
>[!Tip]
>Эндпоинт `/login` использует поле `username` из формы как **email** для поиска пользователя

Замените `existing_user` и `correctPassword` на существующие учетные данные.
Ожидаемый успешный ответ: HTTP-статус `200 OK` и JSON с `access_token` (и, возможно, `token_type`).

10. Аутентификация пользователя с неверными учетными данными (ошибка 401 Unauthorized):
Ожидаемый ответ: HTTP-статус `401 Unauthorized` и JSON с сообщением об ошибке.
11. Информация о текущем аутентифицированном пользователе (эндпоинт `/users/me`):
Для доступа к этому эндпоинту требуется действующий access_token.
- Получите `access_token`: Нужно успешно выполнить запрос на эндпоинт `/login`, чтобы получить `access_token`. Скопируйте полученный токен.
- Выполните GET-запрос к /users/me с заголовком Authorization: Используйте curl для отправки GET-запроса на эндпоинт /users/me. В заголовке запроса вам необходимо передать access_token в формате Bearer <токен>.
Замените <ваш_access_token> на фактический токен, который вы получили после логина:
*Пример curl-запроса:*
```bash
curl -X GET -H "Authorization: Bearer <ваш_access_token>" http://localhost:8000/users/me
```
Если `access_token` действителен, и аутентификация проходит успешно, сервер должен вернуть HTTP-статус `200 OK` и JSON с информацией о текущем пользователе.
12. Отправка письма с верификацией на электронную почту текущего активного пользователя (эндпоинт `/send-verification-email`). Для доступа к этому эндпоинту также требуется действующий `access_token`.
- Получите `access_token`: Нужно успешно выполнить запрос на эндпоинт `/login`, чтобы получить `access_token`. Скопируйте полученный токен.
- Выполните POST-запрос к `/send-verification-email` с заголовком `Authorization`: Используйте `curl` для отправки POST-запроса на эндпоинт `/send-verification-email`. В заголовке запроса передайте `access_token` в формате `Bearer <токен>`.
Замените `<ваш_access_token>` на ваш фактический токен:
*Пример curl-запроса:*
```bash
curl -X POST -H "Authorization: Bearer <ваш_access_token>" http://localhost:8000/send-verification-email
```
Сервер вернёт ответ: {"message": "Verification email sent"} с кодом статуса `202 Accepted`.
13. Вы получили ссылку для верификации по электронной почте (эндпоинт `/verify-email`).
Вам нужно выполнить GET-запрос к URL-адресу верификации, который вы получили в письме. Используйте ваш браузер или `curl` для этого.
Используя браузер:
Скопируйте всю ссылку из письма, которое вам пришло: `http://localhost:8000/verify-email?token=<токен>`
Вставьте эту ссылку в адресную строку веб-браузера и нажмите Enter.
Используя curl:
Вы можете выполнить GET-запрос к этому URL в терминале:
*Пример curl-запроса:*
```bash
curl http://localhost:8000/verify-email?token=<токен>
```
Ожидаемый успешный ответ:
Если токен действителен и обработан успешно, вы должны получить результат:
HTTP-статус `200 OK` с сообщением об успешной верификации (например, `{"message": "Email verified successfully"}`).
14. **Запрос на сброс пароля:**
- Успешный запрос с существующим email:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"email": "existing_user@example.com"}' http://localhost:8000/password-reset-request
```
Ожидаемый результат: HTTP-статус `202` и тело ответа:
```bash
{"message":"If this email address is registered, a password reset link will b
e sent to it."}
```
Проверьте почтовый ящик `existing_user@example.com` на наличие письма со ссылкой.
```
Follow this link to reset your password: http://localhost:8000/password-reset/verify/<token>
```
- Запрос с несуществующим email:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"email": "nonexistent_user@example.com"}' http://localhost:8000/password-reset-request
```
Ожидаемый результат: HTTP-статус `202` и тело ответа:
```bash
{"detail":[{"type":"value_error","loc":["body","email"],"msg":"value is not a
 valid email address: An email address must have an @-sign.","input":"nonexistent_user@example.com","ctx":{"reason":"An email address must have an @-sign."}}]}
```
Убедитесь, что на `nonexistent_user@example.com` письмо не пришло.
- Запрос с невалидным форматом email:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"email": "invalid-email"}' http://localhost:8000/password-reset-request
```
Ожидаемый результат: HTTP-статус `422` и тело ответа с ошибкой валидации:
```bash
{"detail":[{"type":"value_error","loc":["body","email"],"msg":"value is not a
 valid email address: An email address must have an @-sign.","input":"invalid
-email","ctx":{"reason":"An email address must have an @-sign."}}]}
```
- Переход по корректной ссылке с валидным токеном (эмуляция GET-запроса браузера):
Вы просто открываете эту ссылку в браузере. Если вы хотите эмулировать GET-запрос `curl`:

```bash
curl http://localhost:8000/password-reset?token=some_valid_token
```
Ожидаемый результат: HTTP-статус `200` и тело ответа с информацией о токене (форма HTML или JSON в зависимости от вашей реализации). Например, JSON:

```JSON
{"token": "some_valid_token", "email": "existing_user@example.com", "expires_at": "2025-04-24T20:00:00Z"}
```
- Переход по неверной ссылке или с невалидным токеном:
```bash
curl http://localhost:8000/password-reset?token=invalid_token
```
Ожидаемый результат: HTTP-статус `400`.
- Переход по устаревшей ссылке:
Предположим, срок действия токена истек. Выполните тот же запрос, что и с валидным токеном, но с токеном, время действия которого истекло.
```bash
curl http://localhost:8000/password-reset?token=expired_token
```
Ожидаемый результат: HTTP-статус `400`.
- Успешное обновление пароля с валидным токеном и совпадающими новыми паролями:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"token": "some_valid_token", "new_password": "newSecurePassword123", "confirm_new_password": "newSecurePassword123"}' http://localhost:8000/password-reset
```
Ожидаемый результат: HTTP-статус `200`.
После этого пользователь должен успешно войти в систему с паролем `newSecurePassword123`.
- Обновление пароля с несовпадающими новыми паролями:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"token": "some_valid_token", "new_password": "newPassword", "confirm_new_password": "differentPassword"}' http://localhost:8000/password-reset
```
Ожидаемый результат: HTTP-статус `400`.
>[!Tip]
>Пароль пользователя не должен быть изменен
- Обновление пароля с невалидным или истекшим токеном:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"token": "invalid_token", "new_password": "newPassword", "confirm_new_password": "newPassword"}' http://localhost:8000/password-reset
```
Ожидаемый результат: HTTP-статус `400`.
>[!Tip]
>Пароль пользователя не должен быть изменен

15. **Регистрация администратора (доступно только существующим администраторам):**
```bash
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer <ваш_токен_администратора>" -d '{"username": "admin_user", "email": "admin_user@example.com", "password": "admin_password", "role": "admin"}' http://localhost:8000/admin/create-admin
```
16. **Добавление аватара администратора:**
Этот запрос предполагает, что вы уже получили JWT-токен администратора через эндпоинт `/login`.
```bash
$ curl -X POST -H "Authorization: Bearer <ваш_токен_администратора>" -H "Content-Type: application/x-www-form-urlencoded" -d "file=https://...jpg"   http://localhost:8000/users/me/avatar
```
17. **Получение пары токенов (access_token и refresh_token):**
Сначала вам нужно отправить запрос на ваш эндпоинт `/login`, чтобы получить начальную пару токенов.
```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password" \
  http://localhost:8000/login
```
Успешный ответ вернет объект JSON, содержащий access_token, refresh_token и token_type:
```bash
{
  "access_token": "<токен>",
  "refresh_token": "<токен>",
  "token_type": "bearer"
}
```
18. **Доступ к защищенному ресурсу с помощью access_token:**
Доступ к защищенному эндпоинту `/users/me`, используя полученный `access_token` в заголовке `Authorization`
```bash
curl -X GET \
  -H "Authorization: Bearer your_access_token" \
  http://localhost:8000/users/me
```
Успешный ответ вернет объект JSON:
```bash
{"id":4,"username":"<name>","email":"<email>","is_active":true,"
is_verified":true,"created_at":"<date>","avatar_url":"<link>","role":"<role>"}
```
Если токен просрочен или недействителен, вы должны получить ошибку авторизации (обычно статус код 401).
19. **Обновление access_token с помощью refresh_token:**
Если ваш `access_token` просрочился, вы можете использовать `refresh_token` для получения нового `access_token`. Отправьте POST-запрос на эндпоинт `/refresh-token`, передавая refresh_token в теле запроса (как `application/x-www-form-urlencoded`).
```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "refresh_token=your_refresh_token" \
  http://localhost:8000/refresh-token
```
Успешный ответ возвратит новый `access_token`.

[Вверх :arrow_double_up:](#top)

<a id="4"></a>

<img src="https://img.shields.io/badge/4. Пакеты-A9225C?style=for-the-badge"/>

- fastapi
- uvicorn
- sqlalchemy
- psycopg2-binary
- python-dotenv
- pydantic

[Вверх :arrow_double_up:](#top)

<a id="5"></a>

#### <img src="https://img.shields.io/badge/5. Файл .env-583E26?style=for-the-badge"/>

- DATABASE_URL=
- SECRET_KEY=
- MAIL_USERNAME=
- MAIL_PASSWORD=
- MAIL_SERVER=
- MAIL_PORT=
- MAIL_FROM=
- CLOUDINARY_CLOUD_NAME=
- CLOUDINARY_API_KEY=
- CLOUDINARY_API_SECRET=

[Вверх :arrow_double_up:](#top)

<a id="6"></a>

<img src="https://img.shields.io/badge/6. Примечания-A78B71?style=for-the-badge"/>

**1 Удаление существующего контейнера**
- Найдите ID или имя существующего контейнера: Вы можете использовать команду `docker ps -a` для просмотра всех контейнеров (включая остановленные). Найдите контейнер с именем `contacts` и скопируйте его `CONTAINER ID` или убедитесь, что имя указано правильно.
```
docker ps -a
```
*Результат в терминале:*
CONTAINER ID | IMAGE | COMMAND | CREATED | STATUS | PORTS | NAMES
-------------|-------|---------|---------|--------|-------|-------
- Остановите контейнер (если он запущен): Если контейнер находится в состоянии "STATUS" - `Up`, вам нужно сначала его остановить:
```
docker stop <name>
```
- Удалите контейнер: Теперь вы можете удалить контейнер, используя его имя или ID:
```
docker rm <NAME>
```
или
```
docker rm <ID>
```
- Попробуйте запустить свой docker run снова: После удаления старого контейнера вы сможете запустить новый с тем же именем:
```
docker run --name some-postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword -d postgres
```
**2. Переименование существующего контейнера:**
Если вы хотите сохранить существующий контейнер (возможно, для проверки или переноса данных), вы можете его переименовать:

- Переименуйте контейнер: Используйте команду docker rename:
```
docker rename <name> <name>-old
```
Попробуйте запустить свой docker run снова: После переименования старого контейнера вы сможете запустить новый с именем `<name>`.

**3. Повторный запуск контейнера**
```
docker start <name>
```
или
```bash
docker start <CONTAINER_ID_POSTGRES>
```

**4. Проверка порта 5432:**
- Определите процесс, использующий порт 5432:
```
netstat -ano | findstr :5432
```
- Замените `<PID>` на PID, найденный в предыдущей команде
```
tasklist | findstr <PID>
```
- Остановите процесс, использующий порт 5432:
```
taskkill /F /PID <PID>
taskkill /F /IM <имя_процесса>.exe
```

**5. Работа с базой данных:**
- Чтобы увидеть список пользователей:
```sql
\du
```
- Чтобы сменить пароль пользователя postgres (если это необходимо):
```sql
ALTER USER postgres WITH PASSWORD 'новый_пароль';
```
- Перезапустите Docker-контейнер PostgreSQL после внесения изменений, если вы меняли какие-либо настройки внутри контейнера (например, пароль или `pg_hba.conf`), перезапустите контейнер, чтобы изменения вступили в силу:
```bash
docker restart <name>
```
- Подключение к конкретной базе данных (если вы еще не подключены):
```sql
\c <имя_базы_данных>
```
- Просмотр списка таблиц в текущей базе данных:
```sql
\dt
```
или
```sql
\d
```
- Просмотр структуры конкретной таблицы:
```sql
\d <имя_таблицы>
```
- Содержимое таблицы users:
```sql
SELECT * FROM users;
```
или
```sql
SELECT id, username, email, hashed_password FROM users;
```
- Добавление нового столбца. Синтаксис выглядит следующим образом:
```sql
ALTER TABLE <имя_таблицы>
ADD COLUMN <имя_столбца> <тип_данных> <ограничения>;
```
- Чтобы удалить столбец из таблицы:
```sql
ALTER TABLE <имя_таблицы>
DROP COLUMN <имя_столбца>;
```
- SQL-запрос `INSERT` для добавления нового пользователя с ролью 'admin':
```sql
INSERT INTO public.users (username, email, hashed_password, is_active, is_verified, created_at, avatar_url, role)
VALUES ('admin_user', 'admin@example.com', 'your_hashed_admin_password', TRUE, TRUE, NOW(), NULL, 'admin');
```

<a id="redis"></a>

**6. Как проверить и запустить Redis**
1. Проверьте, установлен ли Redis: Если вы еще не устанавливали Redis на свой компьютер, вам нужно это сделать.
***Установка Redis на Windows***
    - Установите Chocolatey, если он еще не установлен:
    >[!Note]
    >Chocolatey - это менеджер пакетов для Windows, который упрощает установку программ

    Откройте PowerShell от имени администратора и выполните следующую команду:

    ```PowerShell
    Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    ```
    - Установите Redis с помощью Chocolatey:
    ```bash
    choco install redis-64
    ```
2. Запуск Redis: После установки Redis должен запуститься как служба Windows автоматически. Вы можете проверить его статус в диспетчере задач (вкладка "Службы") или использовать командную строку:
```bash
net start Redis
```
Для остановки:
```bash
net stop Redis
```
Для перезапуска:
```bash
net restart Redis
```

[Вверх :arrow_double_up:](#top)

<a id="7"></a>

<img src="https://img.shields.io/badge/7. Ошибки-EC9704?style=for-the-badge"/>

```
redis.exceptions.ConnectionError: Error 10061 connecting to localhost:6379. Подключение не установлено, т.к. конечный компьютер отверг запрос на подключение.
```
**Причина ошибки:**
Означает, что ваше FastAPI приложение пытается подключиться к серверу Redis по адресу localhost и порту 6379, но сервер Redis не запущен или недоступен по этому адресу и порту. Конечный компьютер (в данном случае ваш локальный) отклоняет запрос на подключение.
**Решение:**
Вам необходимо убедиться, что сервер Redis запущен и доступен по адресу, который вы указали в переменной окружения REDIS_HOST (в вашем случае, скорее всего, localhost) и порту REDIS_PORT (по умолчанию 6379).
[*Как проверить и запустить Redis*](#redis)

[Вверх :arrow_double_up:](#top)

<a id="8"></a>

<img src="https://img.shields.io/badge/8. Docstrings-9C4A1A?style=for-the-badge"/>

1. Описание docstrings:
- Первая строка: краткий итог того, что делает функция/класс/метод.
- Расширенное описание: Дополнительные детали о функциональности, алгоритмах и т.д.
- Аргументы: описание каждого аргумента, его тип и назначение.
- Returns: Описание возвращаемого значения и его тип.
- Yields: Для генераторов - описание генерируемых значений.
- Raises: Список возможных исключений и условия, при которых они возникают.

[Вверх :arrow_double_up:](#top)