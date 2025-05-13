# kai_mcp_tools.py  – only ONE tool, wraps the existing /analyze logic
from starlette.concurrency import run_in_threadpool
from mcp.server.fastmcp import FastMCP

# Import the FastAPI service exactly as‑is
import service                                     # <‑‑ your original file

mcp = FastMCP("kai-analysis")

@mcp.tool()
async def run_kai_analysis(git_url):
    """
    Clone the repo and run Kai analysis (same work /analyze does).

    Args:
        git_url: URL of the git repository to analyse.

    Returns:
        The JSON result that /analyze already returns.
    """
    # The FastAPI handler is synchronous & CPU‑bound – run it off‑thread.
    body = service.AnalyzeBody(git_url=git_url)
    result = await run_in_threadpool(service.analyze, body)
    return result
