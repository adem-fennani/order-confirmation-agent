from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.api.routes import router
from src.api.dependencies import create_db_tables
import os

app = FastAPI(title="Order Confirmation Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
);

@app.on_event("startup")
async def startup_event():
    await create_db_tables()

# Serve static files from the 'src/web' directory at /static
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "web"), html=True), name="static")

# Redirect / to /static/index.html
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# CORS: allow frontend served from same origin (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000", 
        "http://127.0.0.1:8000",
        "https://504ed128997d.ngrok-free.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 