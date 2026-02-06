from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.map import router as map_router
from api.data import router as data_router
from api.chat import router as chat_router
from api.events import router as events_router

app = FastAPI(title="K-CIA Lite API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(map_router)
app.include_router(data_router)
app.include_router(chat_router)
app.include_router(events_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
