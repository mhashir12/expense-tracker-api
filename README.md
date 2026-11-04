# Expense Tracker API

**Live demo:** https://mhashir.pythonanywhere.com/api/expenses/ (returns `401` until you register and log in with a token; see the endpoints below)

Try it: `POST https://mhashir.pythonanywhere.com/api/register/`, then `POST https://mhashir.pythonanywhere.com/api/token/`, then send the `access` token as `Authorization: Bearer <token>`.

A REST API built with Django and Django REST Framework where each user registers, logs in with JWT, and manages their own expenses. Users can only see and change their own data, and a summary endpoint returns spending totals for a dashboard.

## Features

- User registration and JWT login (access and refresh tokens)
- Full CRUD for expenses (create, read, update, delete)
- Per-user data isolation: a user can never read, edit or delete another user's expenses
- Input validation (amount must be greater than zero, category must be one of a fixed list)
- Filtering, search, ordering and pagination
- Spending summary: overall total, total by category, total by month
- 20 automated tests covering authentication, isolation, validation and totals

## Tech Stack

- Python 3
- Django
- Django REST Framework
- djangorestframework-simplejwt (JWT authentication)
- django-filter
- SQLite (development)

## Setup git 

```bash
# 1. Clone the repository
git clone https://github.com/mhashir12/expense-tracker-api.git
cd expense-tracker-api

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Create the database tables
python manage.py migrate

# 5. (Optional) create an admin user
python manage.py createsuperuser

# 6. Run the server
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/api/`.

## API Endpoints

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/api/register/` | No | Create a new user |
| POST | `/api/token/` | No | Log in, returns `access` and `refresh` tokens |
| POST | `/api/token/refresh/` | No | Get a new access token using a refresh token |
| GET | `/api/expenses/` | Yes | List your expenses (paginated) |
| POST | `/api/expenses/` | Yes | Create an expense |
| GET | `/api/expenses/{id}/` | Yes | Retrieve one of your expenses |
| PUT / PATCH | `/api/expenses/{id}/` | Yes | Update one of your expenses |
| DELETE | `/api/expenses/{id}/` | Yes | Delete one of your expenses |
| GET | `/api/expenses/summary/` | Yes | Total spent, by category and by month |

Authenticated requests must send the header:

```
Authorization: Bearer <access token>
```

### Query parameters for `GET /api/expenses/`

| Parameter | Example | Effect |
|---|---|---|
| `category` | `?category=food` | Only expenses in that category |
| `date` | `?date=2026-10-31` | Only expenses on that date |
| `search` | `?search=canteen` | Search in `description` and `place` |
| `ordering` | `?ordering=-amount` | Sort by `date` or `amount` (prefix `-` for descending) |
| `page` | `?page=2` | Page number (10 results per page) |

Parameters can be combined, e.g. `?category=food&ordering=-amount`.

### Expense fields

| Field | Type | Notes |
|---|---|---|
| `amount` | decimal | Required, must be greater than 0 |
| `category` | string | One of `food`, `transport`, `bills`, `shopping`, `other` (default `other`) |
| `description` | string | Optional |
| `date` | date | Required, format `YYYY-MM-DD` |
| `place` | string | Required |
| `created_at` | datetime | Set automatically |
| `user` | integer | Set automatically from the token, read-only |

## Example Usage

**Register**

```http
POST /api/register/
Content-Type: application/json

{"username": "alice", "email": "alice@example.com", "password": "StrongPass123"}
```

**Log in**

```http
POST /api/token/
Content-Type: application/json

{"username": "alice", "password": "StrongPass123"}
```

**Create an expense**

```http
POST /api/expenses/
Authorization: Bearer <access token>
Content-Type: application/json

{
  "amount": "200.00",
  "category": "transport",
  "description": "Auto fare",
  "date": "2026-10-31",
  "place": "Mathura"
}
```

**Get the summary**

```http
GET /api/expenses/summary/
Authorization: Bearer <access token>
```

## Security Notes

- Passwords are hashed by Django and never returned by the API.
- Every expense query is filtered to the logged-in user, so other users' records return `404`.
- The `user` field is read-only; it is taken from the token, never from the request body.
- Access tokens are short-lived; use the refresh token to get a new one.

## Running Tests

```bash
python manage.py test
```

The suite has 20 tests covering:

- Unauthenticated requests are rejected with `401`
- Users cannot view, edit or delete each other's expenses
- Negative and zero amounts, invalid categories and missing fields return `400`
- The `user` field in a request body is ignored
- Registration hashes passwords; login returns tokens; bearer tokens work
- Summary totals are correct and exclude other users' data

## Author

Mohammad Hashir