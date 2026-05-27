"""FastAPI application for KB-RAG Web UI."""
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

try:
    _version = version("kb-rag-mcp")
except PackageNotFoundError:
    _version = "dev"

# Initialize FastAPI app
app = FastAPI(
    title="KB-RAG Web UI",
    description="Document browser and search tester for KB-RAG system",
    version=_version
)

# Template directory
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "kb-rag-ui"}

@app.get("/")
async def root():
    """Root redirect to browse page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui/browse")
