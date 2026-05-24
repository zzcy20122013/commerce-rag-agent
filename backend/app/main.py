from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.api.catalog import router as catalog_router
from app.api.cart import router as cart_router
from app.api.chat import router as chat_router
from app.api.constraints import router as constraints_router
from app.api.docs import router as docs_router
from app.api.feedback import router as feedback_router
from app.api.products import router as products_router
from app.api.sessions import router as sessions_router
from app.api.upload import router as upload_router
from app.services.image_service import DATA_DIR, ensure_image_dirs


def create_app() -> FastAPI:
    load_dotenv()
    api = FastAPI(title="Commerce RAG Agent", version="0.1.0")
    ensure_image_dirs()
    api.mount("/static", StaticFiles(directory=DATA_DIR), name="static")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(chat_router)
    api.include_router(cart_router)
    api.include_router(catalog_router)
    api.include_router(constraints_router)
    api.include_router(docs_router)
    api.include_router(feedback_router)
    api.include_router(products_router)
    api.include_router(sessions_router)
    api.include_router(upload_router)
    return api


app = create_app()
