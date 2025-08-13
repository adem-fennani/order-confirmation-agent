from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.api.routes import router as api_router
from src.api.facebook_routes import router as facebook_router
from src.api.business import router as business_router
from src.api.dependencies import create_db_tables
import os

app = FastAPI(title="Order Confirmation Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        db_initialized = await create_db_tables()
        if not db_initialized:
            print("[WARNING] Database initialization failed, but continuing startup...")
    except Exception as e:
        print(f"[WARNING] Error during startup: {e}")
        print("[INFO] Continuing startup without database...")

# Serve static files from the 'src/web' directory at /static
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "web"), html=True), name="static")

# Redirect / to /static/internal/index.html
@app.get("/")
async def root():
    return RedirectResponse(url="/static/internal/index.html")

# CORS: allow frontend served from same origin (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.routes import router as api_router
from src.api.facebook_routes import router as facebook_router

# Mount API routes
app.include_router(api_router)
app.include_router(business_router)
# Mount Facebook routes at /api/v1/facebook
app.include_router(facebook_router, prefix="/api/v1/facebook", tags=["facebook"])

# Debug route to verify webhook URL is accessible
@app.get("/api/v1/facebook/webhook/test")
async def test_webhook():
    return {"status": "webhook endpoint is accessible"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug") 