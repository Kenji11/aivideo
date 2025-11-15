from fastapi import FastAPI

# Create app first to ensure it's always available
app = FastAPI()

# Define health endpoint FIRST (before any imports that might fail)
@app.get("/health")
async def health_check():
    """Health check endpoint for ECS"""
    return {"status": "healthy"}

# Try to register additional routers if they exist (non-critical)
try:
    from app.api import health as health_router
    if hasattr(health_router, 'router'):
        app.include_router(health_router.router)
except Exception:
    # Health endpoint already defined above, so we're good
    pass
