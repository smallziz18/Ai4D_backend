# AI4D — Backend for Adaptive AI Learning Platform 🚀

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-6%2F6%20passing-success.svg)](test_corrections.py)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-proprietary-red.svg)](LICENSE)

This repository contains the backend code for AI4D, a **personalized, gamified learning platform** focused on AI and data engineering. It provides intelligent question generation, adaptive user profiling, automated roadmap generation with **real educational resources**, and comprehensive assessment handling using LLMs.

## 🎉 What's New in v2.0.0

- ✨ **MCP (Model Context Protocol)** for automatic resource search (YouTube, Coursera, edX, etc.)
- 🎯 **Smart Level Detection** - Sophisticated algorithm detecting real user level (1-10)
- 🗺️ **Auto-Enriched Roadmaps** - Modules filled with curated videos, courses, and projects
- 🔧 **Event Loop Fixes** - Proper async/await handling in Celery tasks
- 📝 **Postman Test Suite** - 12 pre-configured requests for easy testing
- 📚 **Complete Documentation** - RESUME_FINAL.md, POSTMAN_GUIDE.md, and more

[See full CHANGELOG →](CHANGELOG.md)

## Table of contents

- [Project overview](#project-overview)
- [Key features](#key-features)
- [Quick Start](#quick-start)
- [Architecture overview](#architecture-overview)
- [Requirements](#requirements)
- [Environment variables](#environment-variables)
- [Running services and workers](#running-services-and-workers)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)


## Project overview

AI4D backend implements APIs and background tasks to:

- **Generate personalized quizzes** adapted to user level (via LLM with smart fallback)
- **Analyze questionnaire responses** with sophisticated level detection algorithm
- **Generate adaptive roadmaps** automatically enriched with real educational resources
- **Search and recommend** high-quality learning materials (videos, courses, projects)
- **Track user progression** with gamification (XP, badges, levels)
- **Persist profiles** and activity history (MongoDB + PostgreSQL)
- **Run asynchronous tasks** using Celery (Redis broker)
- **Expose authenticated APIs** for frontend and Postman testing

The repository contains:
- Core API in `src/`
- Celery tasks in `src/celery_tasks.py`
- Profile & roadmap logic in `src/profile/`
- MCP resource search in `src/ai_agents/mcp/`
- Test suite in `test_corrections.py`
- Postman collection in `postman_roadmap_testing.json`


## Key features

### 🎯 Intelligent Profiling
- **Sophisticated level detection** (1-10) based on:
  - Question accuracy rate
  - Weighted scoring (70% open questions + 30% MCQ)
  - Advanced skill detection (CNN, RNN, Transformers, etc.)
  - Automatic level adjustment with bonuses

### 🗺️ Adaptive Roadmaps
- **Auto-generated learning paths** based on user profile
- **Enriched with real resources**:
  - 📹 YouTube videos (Machine Learnia, 3Blue1Brown, etc.)
  - 🎓 Online courses (Coursera, edX, OpenClassrooms, Harvard CS50)
  - 📚 Articles and tutorials
  - 💻 Practical projects (GitHub, Kaggle)
- **Dynamic XP system**: `50 + (level × 5)` for videos, `100 + (level × 10)` for courses

### 🔍 MCP Resource Search
- **Automatic search** of quality educational content
- **Multi-language support** (FR/EN)
- **Level adaptation** (beginner to expert)
- **Curated database** of 50+ high-quality resources

### 🎮 Gamification
- **XP and leveling system**
- **Badges and achievements**
- **Progress tracking** per module and course
- **Energy system** for engagement

### 🔐 Security & Auth
- **JWT authentication** with access/refresh tokens
- **Email verification**
- **Session management** with Redis
- **Proper async handling** in Celery workers


## Quick Start

### Option 1: Automated Script (Recommended)
- LLM integration — calls to an LLM endpoint (local or OpenAI) with fallback profile logic.
- Datastores — Redis (broker/results) and MongoDB (profiles), PostgreSQL for core app data.
- Frontend — a Streamlit app under `streamlit_app/` used for manual testing and demos.


## Requirements

- Python 3.11+ (project used Python 3.12 in development; use compatible Python in your environment)
- Redis (local or Docker)
- MongoDB (local or Docker)
- PostgreSQL (if you use DB features; migrations present under `migrations/`)
- Optional: an LLM endpoint (OpenAI or local LLM) and an API key if using OpenAI


## Environment variables

Create a `.env` file at the project root (the `Settings` class loads it). At minimum provide the following:

- DATABASE_URL - your PostgreSQL URL (if used)
- JWT_SECRET - secret used for JWT token signing
- JWT_ALGORITHM - (optional) default HS256
- REDIS_HOST, REDIS_PORT, REDIS_DB or REDIS_URL
- MONGO_ROOT_USERNAME, MONGO_ROOT_PASSWORD
- MONGO_APP_USERNAME, MONGO_APP_PASSWORD
- MONGO_DATABASE, MONGO_HOST, MONGO_PORT
- DOMAIN - public domain or localhost used for email links
- MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER, MAIL_FROM_NAME
- MAIL_STARTTLS, MAIL_SSL_TLS, USE_CREDENTIALS, VALIDATE_CERTS
- OPENAI_API_KEY - required if you call OpenAI; otherwise ensure your local LLM endpoint is reachable

Example (.env):

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/ai4d
JWT_SECRET=replace-with-secure-secret
REDIS_URL=redis://localhost:6379/0
MONGO_ROOT_USERNAME=root
MONGO_ROOT_PASSWORD=change-me
MONGO_APP_USERNAME=ai4d
MONGO_APP_PASSWORD=change-me
MONGO_DATABASE=ai4d_db
MONGO_HOST=localhost
MONGO_PORT=27017
DOMAIN=http://localhost:8000
MAIL_USERNAME=your@email
MAIL_PASSWORD=your-email-password
MAIL_FROM=your@email
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_FROM_NAME="AI4D Support"
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
USE_CREDENTIALS=true
VALIDATE_CERTS=true
OPENAI_API_KEY=sk-...
```

Security note: Never commit your `.env` or secrets into source control.


## Quickstart (development)

1. Clone and enter the repository

```bash
cd /Users/smallziz/Documents/project\ ai4d/backend_ai4_d
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Ensure Redis and MongoDB are running. You may use Docker or your local installs. Example using Docker Compose (if you have `docker-compose.yml` configured):

```bash
docker-compose up -d redis mongo postgres
```

3. Create `.env` with the required variables.

4. Run database migrations (if you use PostgreSQL migrations present in `migrations/`):

```bash
alembic upgrade head
```

5. Start the API server (example using uvicorn):

```bash
uvicorn src.main:app --reload --port 8000
```

6. Start a Celery worker (important for long tasks):

```bash
celery -A src.celery_tasks worker --loglevel=info
```

7. Run the Streamlit frontend for local UI testing (optional):

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run main.py
```


## Running services and workers

- Celery worker: `celery -A src.celery_tasks worker --loglevel=info`
- To monitor task events: enable `-E` flag or use Flower if configured.
- Make sure Celery uses the same Redis URL as in `Config.REDIS_URL`.

Notes:
- Avoid opening MongoClient before forking workers in production. See PyMongo docs regarding fork safety. In development this warning is shown when creating a client at module import time.
- Long-running LLM generation can take minutes; Celery tasks are used to avoid request timeouts. Configure task time limits carefully if you want no timeout.


## Streamlit frontend (local)

The demo Streamlit app under `streamlit_app/` is intended for manual testing and demonstration. It reads API endpoints from configuration and requires an authenticated user token to access protected endpoints.

Important Streamlit notes you encountered in development:
- Forms must use unique `key` values for each `st.form` instance. If you see `StreamlitAPIException: There are multiple identical forms with key='login_form'`, ensure forms use unique keys or conditional rendering.
- Keep the UI simple: fetch the JSON `question` payload from the `/api/profile/v1/question` API, parse it, and dynamically render the appropriate input widgets per question type.


## Running tests

Run unit tests with pytest:

```bash
pytest -q
```


## Security and best practices

- Protect APIs: all endpoints that return user-specific data should require authentication. Do not expose internal endpoints or secrets.
- Token handling: JWT token expiration and refresh flow must be implemented. Ensure tokens used for email verification have a limited TTL.
- Email verification: verification links should contain short-lived signed tokens and should not expose sensitive data.
- User isolation: one user must never access another user's private data. Enforce checks on each API handler (ownership and authorization checks).
- Secrets: use environment variables or secret management systems (Vault, cloud KMS) in production. Do not store secrets in the repository.


## How profiling and LLM calls work

Profile generation flow in this project:

1. The user completes the generated questionnaire. The frontend composes a response JSON that includes each original question object plus a `user_answer` field. An example structure is included below.
2. The backend receives the completed questionnaire and enqueues a `profile_analysis_task` Celery job.
3. The task calls an LLM (configured either via `OPENAI_API_KEY` for OpenAI or a local LLM endpoint). If the LLM call fails (no API key, model unavailable, or network errors), the task must fall back to deterministic logic and a fallback profile.
4. The resulting profile is persisted to MongoDB and returned as the task result.

Example of the completed questionnaire JSON that your front-end should send (backend expects to copy original question metadata and add user answers):

```json
{
  "score": "6/6",
  "questions_data": [
    {
      "numero": 1,
      "question": "...",
      "type": "ChoixMultiple",
      "options": [],
      "user_answer": "A",
      "correct_answer": "A",
      "is_correct": true
    }
  ]
}
```

Requirements for the front-end payload sent to `profile_analysis_task`:
- Keep the original questions' metadata (numero, question, type, options).
- Add `user_answer` for each question.
- Include any client-side computed score if available.


## Recommendations and TODOs

- Improve LLM usage: allow configurable model names and endpoints; add retries and exponential backoff.
- Make the profile generation output richer: include concrete learning paths, suggested resources, timeline, and next steps derived from answers.
- Add an admin interface to review fallback profiles and re-run analyses when a better LLM endpoint is available.
- Secure Celery/worker environment: avoid opening DB clients at import time (defer client creation to task runtime), or use `forksafe` patterns.
- Add integration tests for the full quiz -> analysis -> profile persistence flow.


## Contributing

1. Fork the repository and create a feature branch.
2. Run tests locally and ensure new code includes tests where appropriate.
3. Create a pull request with a clear description of changes.


