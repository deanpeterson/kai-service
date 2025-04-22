# main.py  – mount regular REST API at "/" and MCP at "/mcp"
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn

from service import app as rest_app           # FastAPI app from the old code
from kai_mcp_tools import mcp                 # registers run_kai_analysis()

app = Starlette(
    routes=[
        Mount("/",   app=rest_app),           # everything works exactly the same
        Mount("/mcp", app=mcp.sse_app()),     # MCP JSON + SSE endpoints
    ]
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
