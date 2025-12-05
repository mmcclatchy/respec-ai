from fastmcp import FastMCP

from .build_plan_tools import register_build_plan_tools
from .feedback_tools_unified import register_unified_feedback_tools
from .loop_tools import register_loop_tools
from .plan_completion_report_tools import register_plan_completion_report_tools
from .project_plan_tools import register_project_plan_tools
from .roadmap_tools import register_roadmap_tools
from .spec_tools import register_spec_tools


def register_all_tools(mcp: FastMCP) -> None:
    register_loop_tools(mcp)
    register_unified_feedback_tools(mcp)
    register_project_plan_tools(mcp)
    register_plan_completion_report_tools(mcp)
    register_roadmap_tools(mcp)
    register_spec_tools(mcp)
    register_build_plan_tools(mcp)
