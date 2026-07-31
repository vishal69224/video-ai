# Video AI Backend

FastAPI backend for the Video AI product. Version 1 focuses on clean architecture and a production-ready upload API. Image analysis, prompt generation, and Kie.ai video generation are scaffolded as placeholders.

> The React frontend currently lives at the repository root (`Video_AI/`) and was intentionally left untouched.

## Folder Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── upload.py
│   │   ├── video.py
│   │   └── status.py
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   ├── schemas/
│   │   ├── upload_schema.py
│   │   └── response_schema.py
│   ├── services/
│   │   ├── upload_service.py
│   │   ├── image_analysis_service.py
│   │   ├── prompt_builder_service.py
│   │   ├── kie_client.py
│   │   └── task_service.py
│   ├── utils/
│   │   ├── file_utils.py
│   │   ├── image_utils.py
│   │   └── validators.py
│   ├── uploads/
│   ├── generated/
│   ├── static/
│   └── main.py
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.13+
- pip

## Installation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # if .env is missing
```

## Run Server

From the `backend/` directory with the virtualenv activated:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Endpoints (V1)

| Method | Path | Status |
|--------|------|--------|
| `GET` | `/` | Welcome |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/upload` | Upload 1–10 images |
| `GET` | `/uploads/{filename}` | Serve uploaded files |
| `POST` | `/api/video/generate` | Placeholder (`501`) |
| `GET` | `/api/status/{task_id}` | Placeholder (`501`) |

### Upload example

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "files=@./sample1.jpg" \
  -F "files=@./sample2.png"
```

Example response:

```json
{
  "success": true,
  "message": "Images uploaded successfully",
  "files": [
    {
      "filename": "a1b2c3d4....jpg",
      "url": "/uploads/a1b2c3d4....jpg",
      "original_filename": "sample1.jpg",
      "size": 123456,
      "content_type": "image/jpeg"
    }
  ]
}
```

Uploaded files are available at:

```text
http://localhost:8000/uploads/<filename>
```

## Environment Variables

See `.env.example` for the full list. Important keys:

| Variable | Description |
|----------|-------------|
| `APP_NAME` | Service display name |
| `DEBUG` | Verbose errors / log level |
| `HOST` / `PORT` | Bind address |
| `UPLOAD_FOLDER` | Relative/absolute upload directory |
| `MAX_UPLOAD_SIZE` | Max bytes per file (default 20 MB) |
| `ALLOWED_EXTENSIONS` | Comma-separated image extensions |
| `KIE_API_KEY` | Reserved for future Kie.ai integration |
| `KIE_BASE_URL` | Reserved for future Kie.ai integration |

## Architecture Notes

- Clean layered design: `api` → `services` → `utils`
- Dependency injection via FastAPI `Depends`
- Async I/O with `aiofiles` / `httpx`
- Loguru for structured console + file logging
- Placeholder services include `TODO` markers for:
  - Image analysis
  - Prompt generation
  - Kie.ai video generation
  - Status polling

## Version 1 Scope

Implemented:

- CORS, lifespan, logging, exception handlers
- Upload validation and storage
- Static `/uploads` mounting
- Swagger / ReDoc

Not implemented yet (intentionally):

- Kie.ai integration
- Prompt generation
- Image analysis
- Auth / database / Redis / Celery
