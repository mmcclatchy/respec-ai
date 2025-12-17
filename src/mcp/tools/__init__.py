from fastmcp import FastMCP

from .document_tools import register_document_tools
from .feedback_tools_unified import register_unified_feedback_tools
from .loop_tools import register_loop_tools


def register_all_tools(mcp: FastMCP) -> None:
    register_loop_tools(mcp)
    register_unified_feedback_tools(mcp)
    register_document_tools(mcp)
