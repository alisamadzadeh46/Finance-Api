# Finance API 💳

> A secure financial REST API built with **Django 6** and **Django REST Framework**, featuring httpOnly cookie-based JWT authentication, KYC identity verification, and transaction PIN support.

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6 + Django REST Framework |
| Authentication | SimpleJWT + Token Blacklisting |
| Database | SQLite (dev) |
| Language | Python 3.13 |

---

## ✨ Features

- ✅ Custom JWT auth with **httpOnly cookie** refresh tokens (XSS-safe)
- ✅ Short-lived access tokens (15 min) + long-lived refresh tokens (14 days)
- ✅ **Token rotation & blacklisting** after logout
- ✅ **KYC identity verification** system (National ID, Driver's License, Passport)
- ✅ KYC status workflow: `UNVERIFIED → PENDING → VERIFIED / REJECTED`
- ✅ **Transaction PIN** per user for confirming financial operations
- ✅ Email-based authentication (not username)
- ✅ Custom User model extending AbstractUser

---

## 🔐 Authentication Flow

```
Register → access token (body) + refresh token (httpOnly cookie)
Login    → access token (body) + refresh token (httpOnly cookie)
Refresh  → new access token (reads refresh from cookie automatically)
Logout   → blacklists refresh token + clears cookie
```

> Refresh tokens are **never exposed to JavaScript** — stored only in httpOnly cookies.

---

## 📁 Project Structure

```
Finance-Api/
├── FinanceApi/
│   ├── settings.py       # JWT config, auth settings
│   ├── urls.py
│   └── wsgi.py
├── users/
│   ├── models.py         # User, KYC models
│   ├── serializers.py    # Register, login serializers
│   ├── views.py          # Auth views
│   └── urls.py
└── manage.py
```

---

## 🔗 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/users/register/` | Register new user | ❌ |
| POST | `/api/users/login/` | Login & get tokens | ❌ |
| POST | `/api/users/logout/` | Logout & blacklist token | ✅ |
| POST | `/api/users/token/refresh/` | Refresh access token via cookie | ❌ |
| GET | `/api/users/me/` | Get current user info | ✅ |

---

## 👤 User Model

```python
class User(AbstractUser):
    email = models.EmailField(unique=True)       # Used as USERNAME_FIELD
    username = models.CharField(unique=True)
    transaction_pin = models.CharField(...)      # For confirming transactions
```

---

## 🪪 KYC Model

```python
class KYC(models.Model):
    user               # OneToOne → User
    full_name
    date_of_birth
    id_type            # NATIONAL_ID | DRIVERS_LICENSE | PASSPORT
    id_image           # Document image URL
    verification_status  # UNVERIFIED | PENDING | VERIFIED | REJECTED
```

---

## ⚙️ JWT Configuration

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_COOKIE_SAMESITE": "None",
    "AUTH_COOKIE_SECURE": True,
}
```

---

## 🚀 Getting Started

```bash
git clone https://github.com/alisamadzadeh46/Finance-Api.git
cd Finance-Api

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## ⚠️ Security Notes

- Change `SECRET_KEY` before deploying to production
- Switch `DEBUG` to `False` in production
- Replace SQLite with PostgreSQL for production use
- Set `ALLOWED_HOSTS` properly before deployment

---

## 📄 License

MIT License

---

<p align="center">Made with ❤️ by <a href="https://github.com/alisamadzadeh46">Ali Samadzadeh</a></p>
