from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.api.routes import router as api_router
from src.api.facebook_routes import router as facebook_router
from src.api.dependencies import create_db_tables
import os
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Order Confirmation Agent API", version="1.0.0")

# Get ngrok public URL
try:
    ngrok_auth_token = os.environ.get("NGROK_AUTHTOKEN")
    if ngrok_auth_token:
        ngrok.set_auth_token(ngrok_auth_token)
    public_url = ngrok.connect(8000)
    print(f"ngrok tunnel {public_url} -> http://127.0.0.1:8000")
    ngrok_url = public_url.public_url
except Exception as e:
    print(f"[WARNING] Could not start ngrok: {e}")
    ngrok_url = None


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
    try:
        db_initialized = await create_db_tables()
        if not db_initialized:
            print("[WARNING] Database initialization failed, but continuing startup...")
    except Exception as e:
        print(f"[WARNING] Error during startup: {e}")
        print("[INFO] Continuing startup without database...")

# Serve static files from the 'src/web' directory at /static
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "web"), html=True), name="static")

# Redirect / to /static/index.html
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# CORS: allow frontend served from same origin (localhost:8000)
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if ngrok_url:
    origins.append(ngrok_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.routes import router as api_router
from src.api.facebook_routes import router as facebook_router

# Mount API routes
app.include_router(api_router)
# Mount Facebook routes at /api/v1/facebook
app.include_router(facebook_router, prefix="/api/v1/facebook", tags=["facebook"])

# Debug route to verify webhook URL is accessible
@app.get("/api/v1/facebook/webhook/test")
async def test_webhook():
    return {"status": "webhook endpoint is accessible"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 