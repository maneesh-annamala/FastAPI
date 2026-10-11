# 🚀 FastAPI Blog Application — Daily Learning Project

A full-stack asynchronous Blog application built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL (`asyncpg`)**, **Alembic (Database Migrations)**, **Pydantic v2**, **Jinja2 Templates**, **Pillow (Image Processing)**, **AWS S3 (Cloud Media Storage)**, **aiosmtplib (Email System)**, and **JWT Authentication**. 

> 📌 **Learning Journey**: This repository records my daily progress as I learn and master FastAPI, moving from fundamental concepts to advanced asynchronous patterns, clean architecture, and full-stack web development.

---

## ✨ Features Built So Far

- **⚡ Asynchronous Database Architecture**: Fully async database interactions powered by **PostgreSQL**, `asyncpg`, **SQLAlchemy 2.0**, and FastAPI `lifespan` context manager.
- **🔄 Database Schema Migrations (Alembic)**: 
  - Version-controlled schema migrations with **Alembic**.
  - Async migration execution configured in `alembic/env.py` loading database credentials dynamically from Pydantic `Settings`.
  - Auto-generation of migration scripts (`alembic revision --autogenerate`) for seamless schema evolution and rollbacks (`alembic upgrade / downgrade`).
- **🔐 Secure Authentication & Authorization**:
  - JWT Access Token generation & verification using `PyJWT`.
  - Secure password hashing using **Argon2** via `pwdlib`.
  - OAuth2 Password Bearer flow for API authentication.
- **🔑 Password Reset & Email Integration**:
  - Secure token generation via `secrets.token_urlsafe(32)` with SHA-256 token hashing stored in `PasswordResetToken` table model.
  - Asynchronous SMTP email dispatching powered by **`aiosmtplib`** integrated with FastAPI `BackgroundTasks`.
  - Responsive Jinja2 HTML email template (`templates/email/password_reset.html`) with customizable reset URLs and automatic 30-minute token expiration.
  - Comprehensive API Endpoints:
    - `POST /api/users/forgot-password`: Generates reset token and triggers async email delivery (with generic anti-enumeration response).
    - `POST /api/users/reset-password`: Validates token, hashes new password, and invalidates used reset token.
    - `PATCH /api/users/me/password`: Authenticated password change endpoint with immediate reset token cleanup.
- **☁️ Profile Picture Upload & AWS S3 Cloud Storage**:
  - Cloud media storage powered by **AWS S3** using `boto3`.
  - **Pillow (PIL)** integration for background thread image manipulation (`run_in_threadpool`).
  - Automatic EXIF orientation correction, square crop & resize to 300x300, RGB mode conversion, and JPEG compression optimization.
  - Asynchronous S3 upload (`_upload_to_s3`) and deletion (`_delete_from_s3`) under `profile_pics/{uuid}.jpg` key.
  - S3 public media URL resolution via `Users.image_path` model property (`https://<bucket>.s3.<region>.amazonaws.com/profile_pics/<filename>`) with fallback to local default avatar.
  - Included AWS IAM policy (`aws_iam_policy.json`), S3 Bucket policy (`aws_bucket_policy.json`), detailed policy guide (`aws_policies_explanations.txt`), and S3 credential verification script (`check_s3.py`).
- **📄 Posts & User Posts Pagination**:
  - **Paginated API Endpoints**: `/api/posts` and `/api/users/{user_id}/posts` support `skip` and `limit` query parameters, returning a `PaginatedPostsResponse` schema (`total`, `skip`, `limit`, `has_more`, `posts`).
  - **Interactive "Load More" Feed**: Client-side async pagination on Home and User Posts pages via JavaScript Fetch API and dynamic DOM injection.
  - **Database Efficiency**: Optimized count and slice queries using SQLAlchemy `func.count()`, `offset()`, and `limit()`.
- **📝 Post & User Management**:
  - Relational Database Models with `Users`, `Posts`, and `PasswordResetToken` mapped via SQLAlchemy ORM.
  - Eager loading with `selectinload` for optimized N+1 query prevention.
- **🎨 Hybrid Layout (Web UI + REST API)**:
  - **Jinja2 Templates**: Dynamic server-side rendering for `Home`, `Login`, `Register`, `Account`, `Post detail`, and `User Posts` pages.
  - **Interactive Client Features**: Live image preview, AJAX multipart profile upload, dynamic UI authentication state updates, and async load-more feeds.
  - **API Endpoints**: Modularized router architecture under `/routers`.
- **🛠️ Smart Exception Handling**:
  - Dual response system handling errors gracefully: returning JSON for `/api` requests and custom styled HTML (`error.html`) for browser requests.
- **🧪 Comprehensive Automated Testing Suite (pytest)**:
  - 100% endpoint coverage with 52 automated tests spanning all REST API routes and Jinja2 template views.
  - **Asynchronous Test Client**: High-performance async HTTP requests via `httpx.AsyncClient` powered by `anyio`.
  - **Database Transaction Isolation**: Clean per-test database isolation utilizing SQLAlchemy `NullPool`, connection savepoints, and automatic rollbacks in `conftest.py` — zero database pollution between test runs.
  - **AWS S3 Mocking with `moto`**: Full cloud storage emulation with `moto.mock_aws` to test multipart profile picture uploads and S3 file deletion safely without live AWS credentials.
  - **Mocked Background Tasks**: Asynchronous SMTP email verification using `unittest.mock.AsyncMock` to validate password reset token generation and delivery.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Language** | Python 3.13+ |
| **Database** | [PostgreSQL](https://www.postgresql.org/) |
| **Async DB Driver & ORM** | `asyncpg` + [SQLAlchemy 2.0](https://www.sqlalchemy.org/) |
| **Database Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Cloud Storage** | [AWS S3](https://aws.amazon.com/s3/) via `boto3` |
| **Validation & Settings** | [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings` |
| **Auth & Security** | `PyJWT`, `pwdlib` (Argon2), `hashlib`, `secrets` |
| **Email & Async SMTP** | `aiosmtplib`, Jinja2 HTML Templates |
| **Image Processing** | [Pillow (PIL)](https://python-pillow.org/) |
| **Testing & Mocking** | [pytest](https://pytest.org/), `anyio`, [HTTPX](https://www.python-httpx.org/), [Moto](http://docs.getmoto.org/) (AWS S3 mock) |
| **Templating** | Jinja2 Templates + HTML/CSS Static Files |
| **Package Manager** | [`uv`](https://github.com/astral-sh/uv) |

---

## 📂 Project Structure

```text
project_blogs/
├── alembic/
│   ├── versions/          # Database revision scripts (schema migrations)
│   ├── env.py             # Alembic migration environment (async config & SQLAlchemy metadata)
│   └── script.py.mako     # Migration template script
├── core/
│   └── config.py          # Environment settings using pydantic-settings (DATABASE_URL, SecretStr, S3, SMTP)
├── routers/
│   ├── posts.py           # API routes for blog post operations with pagination
│   └── users.py           # API routes for auth, password reset, profile pictures & paginated user posts
├── static/                # CSS, JS, icons, default avatar images
├── templates/             # Jinja2 HTML templates (layout, home, login, user_posts, etc.)
│   └── email/
│       └── password_reset.html # Responsive HTML email template for password reset
├── tests/                 # Automated test suite (52 tests, 100% endpoint coverage)
│   ├── conftest.py        # Async DB savepoint fixtures, moto S3 client, and test client setup
│   ├── test_image.jpg     # Sample image asset for profile picture upload testing
│   ├── test_post.py       # Full CRUD, pagination, and authorization tests for /api/posts
│   ├── test_users.py      # Registration, auth, profile picture, and password management tests
│   └── test_views.py      # Server-rendered HTML template view tests (main.py)
├── alembic.ini            # Alembic configuration settings
├── auth.py                # Password hashing, JWT access token & SHA-256 reset token utilities
├── aws_bucket_policy.json # AWS S3 public read bucket policy reference
├── aws_iam_policy.json   # AWS IAM minimal permission policy for app user
├── aws_policies_explanations.txt # Detailed explanation for S3 & IAM policy setup
├── check_s3.py            # Utility script to verify S3 credentials & upload permissions
├── database.py            # Async PostgreSQL engine setup & session dependency injection
├── email_utils.py         # Async SMTP email dispatching via aiosmtplib & Jinja2 rendering
├── image_utils.py         # Pillow image cropping/resizing & AWS S3 upload/delete utilities
├── main.py                # App entrypoint, lifespan manager, Jinja rendering & error handlers
├── models.py              # SQLAlchemy ORM models (Users, Posts, PasswordResetToken)
├── populates_db.py        # Database seed script for test users, posts, and profile images
├── schemas.py             # Pydantic schemas (UserCreate, ForgetPasswordRequest, ResetPasswordRequest, etc.)
├── .env.example           # Template for environment configuration including S3 & PostgreSQL settings
├── .gitignore             # Ignored files (secrets, venv, media cache)
├── pyproject.toml         # Dependency definitions managed by uv
└── uv.lock                # Lockfile for reproducible builds
```

---

## ⚙️ Getting Started

### Prerequisites
- **Python 3.13+**
- **PostgreSQL Database** running locally or remotely
- **AWS S3 Bucket** configured for media storage
- **uv** package manager installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation & Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/project_blogs.git
   cd project_blogs
   ```

2. **Sync virtual environment & dependencies with `uv`**:
   ```bash
   uv sync
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *(Set your PostgreSQL connection string `DATABASE_URL`, `SECRET_KEY`, SMTP email settings, and AWS S3 credentials in `.env`)*:
   ```env
   S3_BUCKET_NAME=your-s3-bucket-name
   S3_REGION=ap-southeast-2
   S3_ACCESS_KEY_ID=your-access-key-id
   S3_SECRET_ACCESS_KEY=your-secret-access-key
   ```

4. **Verify AWS S3 Connection**:
   Run the S3 verification script to confirm bucket upload and delete permissions:
   ```bash
   uv run python check_s3.py
   ```

5. **Run Database Migrations with Alembic**:
   Apply all schema migrations to create database tables in PostgreSQL:
   ```bash
   uv run alembic upgrade head
   ```

6. **(Optional) Populate Sample Seed Data**:
   Populate the database with initial users, blog posts, and avatars:
   ```bash
   uv run python populates_db.py
   ```

7. **Run the FastAPI Development Server**:
   ```bash
   uv run uvicorn main:app --reload
   ```

8. **Access the Application**:
   - 🌐 **Web Interface**: `http://127.0.0.1:8000/`
   - 📚 **Swagger Interactive API Docs**: `http://127.0.0.1:8000/docs`

9. **Run Automated Test Suite (pytest)**:
   Execute all 52 tests with async execution, DB rollback isolation, and S3 mocking:
   ```bash
   uv run pytest
   ```
   Run with detailed output and verbosity:
   ```bash
   uv run pytest -v
   ```

---

## 🔄 Useful Alembic Migration Commands

- **Create a new migration after updating SQLAlchemy models**:
  ```bash
  uv run alembic revision --autogenerate -m "description of changes"
  ```
- **Apply pending migrations**:
  ```bash
  uv run alembic upgrade head
  ```
- **Roll back the last migration**:
  ```bash
  uv run alembic downgrade -1
  ```
- **Check current migration status**:
  ```bash
  uv run alembic current
  ```

---

## 📅 Daily Learning Log

| Day | Date | Key Highlights / Progress |
| :---: | :---: | :--- |
| **Day 1** | Initial Commit | Set up FastAPI application structure, async SQLAlchemy database engine (`aiosqlite`), ORM models (`Users`, `Posts`), JWT authentication with Argon2 hashing, modular routers, Jinja2 template rendering, and error handlers. |
| **Day 2** | Profile Picture Feature | Integrated **Pillow (PIL)** for avatar upload processing (300x300 cropping, EXIF rotation, optimization), UUID file management, media mounting, dynamic frontend previews, and user picture upload/delete endpoints. |
| **Day 3** | Posts & User Posts Pagination | Added offset & limit pagination to `/api/posts` and `/api/users/{user_id}/posts` with `PaginatedPostsResponse` schema, total post counting via `func.count()`, and interactive "Load More Posts" AJAX feeds on Home and User Posts pages. |
| **Day 4** | Password Reset & Email Integration | Built asynchronous backend password reset flow (`/forgot-password`, `/reset-password`, `/me/password`), `PasswordResetToken` table model with SHA-256 token hashing, `aiosmtplib` async SMTP background email delivery, and HTML email templates. |
| **Day 5** | PostgreSQL & Alembic Migrations | Upgraded database architecture from SQLite to **PostgreSQL** (`postgresql+asyncpg`). Integrated **Alembic** schema migrations with async database connection support (`alembic/env.py`). Created baseline schema migration and initial schema updates (`likes` column on `posts`). |
| **Day 6** | AWS S3 Cloud Media Storage | Migrated user profile picture storage from local disk to **AWS S3**. Integrated `boto3` for asynchronous S3 upload (`_upload_to_s3`) and deletion (`_delete_from_s3`), updated `Users.image_path` property to return full S3 URLs, added AWS IAM & Bucket policy files, and created `check_s3.py` connection verification tool. |
| **Day 7** | Comprehensive Testing Suite with Pytest | Implemented 100% automated test coverage across all 52 tests using **pytest**, `anyio`, and `httpx.AsyncClient`. Configured database transaction rollback isolation with savepoints (`NullPool`), AWS S3 cloud mocking with `moto.mock_aws`, async background task email mocking, and end-to-end tests for all Posts & Users REST endpoints and Jinja2 frontend routes. |

---

## 🛡️ License

This project is open-source and available under the [MIT License](LICENSE).
