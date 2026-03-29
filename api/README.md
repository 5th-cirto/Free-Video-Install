# API service

## Run

```powershell
cd d:\vue_project\free-video-installer
python -m uvicorn api.main:app --reload --port 8000
```

## Endpoints

- `GET /api/health`
- `POST /api/video/inspect`
- `POST /api/video/download`
- `POST /api/video/download/batch`
- `GET /api/video/tasks`
- `GET /api/video/tasks/{task_id}`

