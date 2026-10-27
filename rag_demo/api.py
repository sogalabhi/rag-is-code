"""Local API for complete, source-validated answers. No answer streaming."""
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None, override=False):
        p = Path(path) if path else ROOT / ".env"
        if not p.is_file():
            return
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip("'\"")
            if override or key not in os.environ:
                os.environ[key] = val

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .grounding import GroundingError
from .providers import ProviderError
from .service import RAGService

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)
logger = logging.getLogger(__name__)


class HistoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=8000)


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)
    method: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    top_k: int = Field(default=3, ge=1, le=8)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=12)
    context: dict[Literal["member_type", "connection_type"], Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def trim_context(cls, value):
        if any(not item.strip() for item in value.values()):
            raise ValueError("Context must not be blank.")
        return {key: item.strip() for key, item in value.items()}


def create_app(service=None):
    application = FastAPI(title="The Codebook API", version="0.1.0")
    application.state.service = service
    service_lock = Lock()

    def get_service():
        with service_lock:
            if application.state.service is None:
                application.state.service = RAGService()
        return application.state.service

    @application.get("/api/health")
    def health():
        try:
            engine = get_service()
        except (ValueError, OSError):
            raise HTTPException(503, {"code": "corpus_unavailable", "message": "The source collection is unavailable."}) from None
        return {"status": "ok", "corpus_records": len(engine.chunks), "streaming": False,
                "generation_configured": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
                "methods": ["keyword", "semantic", "hybrid"]}

    @application.post("/api/answer")
    def answer(request: QuestionRequest):
        try:
            return get_service().answer(request.question, request.method, request.top_k,
                                        [turn.model_dump() for turn in request.history], request.context)
        except GroundingError:
            raise HTTPException(502, {"code": "invalid_answer", "message": "The generated answer did not pass source validation. Please retry."}) from None
        except ProviderError as exc:
            raise HTTPException(503, {"code": "provider_unavailable", "message": str(exc),
                                      "retryable": exc.retryable}) from None
        except ValueError as exc:
            message = "Supply a question with content search terms." if "content search terms" in str(exc) else "Search could not be initialized. Check the server setup and retry."
            raise HTTPException(422 if "content search terms" in str(exc) else 503,
                                {"code": "invalid_question" if "content search terms" in str(exc) else "retrieval_unavailable", "message": message}) from None
        except (OSError, RuntimeError) as exc:
            logger.error("Answer preparation failed (%s).", type(exc).__name__)
            raise HTTPException(503, {"code": "service_unavailable", "message": "The answer service is unavailable. Please retry."}) from None

    @application.get("/api/reference/{name}")
    def reference(name: str):
        files = {"codebook.pdf": ROOT / "data/is.800.2007.pdf"}
        files.update({name: ROOT / "data/review_assets" / name for name in
                      ("table-05.png", "table-19.png", "figure-05.png")})
        path = files.get(name)
        if path is None or not path.is_file():
            raise HTTPException(404, "Reference file not found.")
        return FileResponse(path, media_type="application/pdf" if name.endswith(".pdf") else "image/png")

    frontend = ROOT / "prototype/dist"
    if (frontend / "index.html").is_file():
        application.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rag_demo.api:app", host="127.0.0.1", port=8000)
