<a id="top"></a>

<a href="#1"><img src="https://img.shields.io/badge/Creating and connecting to a database-512BD4?style=for-the-badge"/></a> <a href="#2"><img src="https://img.shields.io/badge/Run API-ECD53F?style=for-the-badge"/></a> <a href="#3"><img src="https://img.shields.io/badge/API Functionality Overview-007054?style=for-the-badge"/></a> <a href="#4"><img src="https://img.shields.io/badge/Packages-A9225C?style=for-the-badge"/></a>
<a href="#5"><img src="https://img.shields.io/badge/File .env-18AEFF?style=for-the-badge"/></a>

<a id="1"></a>

#### <img src="https://img.shields.io/badge/1. Creating and connecting to a database-512BD4?style=for-the-badge"/>
In this work, we will use a postgres database.

Make sure you have the PostgreSQL server running and the database specified in the `.env` file created.

At the command line, start the Docker container:

```bash
docker run --name some-postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword -d postgres
```
Instead of `some-postgres`, choose your container name, and instead of `mysecretpassword`, come up with your password to connect to the database.

SQLAlchemy will automatically create the `contacts` table the first time the API is run thanks to the line in the `main.py` file:
```python
database.Base.metadata.create_all(bind=database.engine)
```
**Creating a "contacts" database in PostgreSQL:**
1. Go to the PostgreSQL Docker container:
```bash
docker exec -it contacts bash
```
2. Switch to the `name` user, for example, `postgres`:
```bash
su postgres
```
3. Start the `psql` client:
```bash
psql
```
>[!note]
>You should see the command line `postgres=#`.
4. Create the "contacts" database:
```sql
CREATE DATABASE contacts;
```
5. Check the list of existing databases:
```sql
\l
```
6. Exit `psql` and the container:
```sql
\q
exit
exit
```

[Top :arrow_double_up:](#top)

<a id="2"></a>

#### <img src="https://img.shields.io/badge/2. Run API-ECD53F?style=for-the-badge"/>
Make sure you are in the root directory of the project (where the `main.py` file is located) and run the API using Uvicorn:
```
uvicorn main:app --reload
```
Once launched, you will be able to access the Swagger documentation at `http://127.0.0.1:8000/docs` or `http://127.0.0.1:8000/redoc`.

[Top :arrow_double_up:](#top)

<a id="3"></a>

#### <img src="https://img.shields.io/badge/3. API Functionality Overview-007054?style=for-the-badge"/>
- POST /contacts/: Create a new contact. Expects a JSON request body with contact data.
- GET /contacts/: Get a list of all contacts. Supports pagination using `skip` and `limit` parameters, as well as filtering by `first_name`, `last_name`, and `email` via query parameters.
- GET /contacts/{contact_id}: Get a single contact by its ID.
- PUT /contacts/{contact_id}: Update an existing contact by its ID. Expects a JSON request body with updated data.
- DELETE /contacts/{contact_id}: Delete a contact by its ID.
- GET /contacts/birthdays/upcoming: Get a list of contacts with a birthday in the next 7 days.

>[!Tip]
>The get_upcoming_birthdays function correctly handles birthdays falling on February 29, even in non-leap years, treating them as February 28 for the purposes of determining upcoming birthdays within the next week.

[Top :arrow_double_up:](#top)

<a id="4"></a>

#### <img src="https://img.shields.io/badge/4. Packages-A9225C?style=for-the-badge"/>
- fastapi
- uvicorn
- sqlalchemy
- psycopg2-binary
- python-dotenv
- pydantic

[Top :arrow_double_up:](#top)

<a id="5"></a>

#### <img src="https://img.shields.io/badge/4. File .env-18AEFF?style=for-the-badge"/>

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

[Top :arrow_double_up:](#top)
