# API service

## Run

```powershell
cd d:\vue_project\free-video-installer
python -m uvicorn api.main:app --reload --port 8000
```

## Endpoints

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me` (Bearer token required)
- `POST /api/auth/request-password-reset`
- `POST /api/auth/reset-password`
- `POST /api/billing/checkout-session` (Bearer token required)
- `GET /api/billing/membership-status` (Bearer token required)
- `GET /api/billing/orders` (Bearer token required)
- `POST /api/billing/webhook` (Stripe callback)
- `POST /api/billing/mock/webhook-paid` (dev-only offline test, Bearer token required)
- `POST /api/video/inspect`
- `POST /api/video/download`
- `POST /api/video/download/batch`
- `GET /api/video/tasks`
- `GET /api/video/tasks/{task_id}`
- `POST /api/ai-summary/stream` (Bearer token required, free quota 5/day, VIP unlimited)

