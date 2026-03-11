from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from src.shared import state_manager


def register_review_section_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def store_review_section(key: str, content: str, ctx: Context) -> str:
        """Store a review section as raw markdown at a hierarchical key.

        Used by reviewer agents to store review results. Overwrites any existing
        content at the same key.

        Parameters:
        - key: Hierarchical key (e.g., "plan-name/phase-name/review-quality-check")
        - content: Review section markdown content

        Returns:
        - str: Confirmation message
        """
        if not key or not content:
            raise ToolError('key and content cannot be empty')

        await ctx.info(f'Storing review section at {key}')
        result = await state_manager.store_review_section(key, content)
        await ctx.info(f'Stored review section at {key}')
        return result

    @mcp.tool()
    async def get_review_section(key: str, ctx: Context) -> str:
        """Retrieve a review section's raw markdown content.

        Parameters:
        - key: Hierarchical key (e.g., "plan-name/phase-name/review-quality-check")

        Returns:
        - str: Raw markdown content
        """
        if not key:
            raise ToolError('key cannot be empty')

        await ctx.info(f'Retrieving review section at {key}')
        try:
            result = await state_manager.get_review_section(key)
            await ctx.info(f'Retrieved review section at {key}')
            return result
        except ValueError as e:
            await ctx.error(str(e))
            raise ToolError(str(e)) from e

    @mcp.tool()
    async def list_review_sections(parent_key: str, ctx: Context) -> str:
        """List review section keys matching a parent key prefix.

        Parameters:
        - parent_key: Parent key prefix (e.g., "plan-name/phase-name")

        Returns:
        - str: Comma-separated list of matching keys, or message if none found
        """
        if not parent_key:
            raise ToolError('parent_key cannot be empty')

        await ctx.info(f'Listing review sections under {parent_key}')
        keys = await state_manager.list_review_sections(parent_key)
        await ctx.info(f'Found {len(keys)} review sections under {parent_key}')
        if not keys:
            return f'No review sections found under {parent_key}'
        return ', '.join(keys)
