"""Webhook receiver — FastAPI app that receives events from Gitea."""
import logging
import sys

from fastapi import FastAPI

sys.path.insert(0, "/app")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(title="AI Company Webhook Receiver", version="1.0.0")

from routes.github import router as github_router
from routes.health import router as health_router

app.include_router(health_router)
app.include_router(github_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
