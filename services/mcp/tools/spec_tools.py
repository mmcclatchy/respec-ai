from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from services.models.spec import TechnicalSpec
from services.shared import state_manager
from services.utils.enums import LoopStatus
from services.utils.errors import LoopNotFoundError, RoadmapNotFoundError, SpecNotFoundError
from services.utils.loop_state import MCPResponse
from services.utils.state_manager import StateManager


class SpecTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    def store_spec(self, project_name: str, spec_name: str, spec_markdown: str) -> str:
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not spec_name:
            raise ToolError('Spec name cannot be empty')
        if not spec_markdown:
            raise ToolError('Spec markdown cannot be empty')

        try:
            spec = TechnicalSpec.parse_markdown(spec_markdown)
            # Phase name extracted from H1 header is canonical source
            # Validation ensures H1 format: # Technical Specification: {kebab-case-name}
            self.state.store_spec(project_name, spec)
            return f'Stored spec "{spec_name}" in project {project_name} (iteration {spec.iteration}, version {spec.version})'
        except RoadmapNotFoundError as e:
            raise ResourceError(str(e))
        except ValidationError:
            raise ToolError('Invalid specification data provided')
        except Exception as e:
            raise ToolError(f'Failed to store spec: {str(e)}')

    def update_spec(self, project_name: str, spec_name: str, updated_markdown: str) -> str:
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not spec_name:
            raise ToolError('Spec name cannot be empty')
        if not updated_markdown:
            raise ToolError('Updated markdown cannot be empty')

        try:
            updated_spec = TechnicalSpec.parse_markdown(updated_markdown)
            return self.state.update_spec(project_name, spec_name, updated_spec)
        except SpecNotFoundError as e:
            raise ResourceError(f'Spec not found: {str(e)}')
        except ValidationError:
            raise ToolError('Invalid specification data provided')
        except Exception as e:
            raise ToolError(f'Failed to update spec: {str(e)}')

    def get_spec_markdown(self, project_name: str | None, spec_name: str | None, loop_id: str | None) -> MCPResponse:
        try:
            if loop_id:
                loop_state = self.state.get_loop(loop_id)
                spec = self.state.get_spec_by_loop(loop_id)
                markdown = spec.build_markdown()
                char_length = len(markdown)
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message=markdown,
                    char_length=char_length,
                )
            if project_name and spec_name:
                spec = self.state.get_spec(project_name, spec_name)
                markdown = spec.build_markdown()
                char_length = len(markdown)
                return MCPResponse(
                    id=f'{project_name}/{spec_name}',
                    status=LoopStatus.COMPLETED,
                    message=markdown,
                    char_length=char_length,
                )
            raise ToolError('Either loop_id OR (project_name AND spec_name) must be provided')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist or is not linked to a spec')
        except RoadmapNotFoundError as e:
            raise ResourceError(str(e))
        except SpecNotFoundError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to retrieve spec: {str(e)}')

    def list_specs(self, project_name: str) -> MCPResponse:
        if not project_name:
            raise ToolError('Project name cannot be empty')

        try:
            spec_names = self.state.list_specs(project_name)
            if not spec_names:
                return MCPResponse(
                    id=project_name, status=LoopStatus.COMPLETED, message=f'No specs found in project {project_name}'
                )

            spec_list = ', '.join(spec_names)
            return MCPResponse(
                id=project_name,
                status=LoopStatus.COMPLETED,
                message=f'Found {len(spec_names)} spec{"s" if len(spec_names) != 1 else ""} in project {project_name}: {spec_list}',
            )
        except RoadmapNotFoundError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to list specs: {str(e)}')

    def resolve_spec_name(self, project_name: str, partial_name: str) -> tuple[str | None, list[str]]:
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not partial_name:
            raise ToolError('Partial name cannot be empty')

        try:
            return self.state.resolve_spec_name(project_name, partial_name)
        except Exception as e:
            raise ToolError(f'Failed to resolve spec name: {str(e)}')

    def delete_spec(self, project_name: str, spec_name: str) -> MCPResponse:
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not spec_name:
            raise ToolError('Spec name cannot be empty')

        try:
            was_deleted = self.state.delete_spec(project_name, spec_name)
            if was_deleted:
                return MCPResponse(
                    id=f'{project_name}/{spec_name}',
                    status=LoopStatus.COMPLETED,
                    message=f'Deleted spec "{spec_name}" from project {project_name}',
                )
            else:
                return MCPResponse(
                    id=f'{project_name}/{spec_name}',
                    status=LoopStatus.COMPLETED,
                    message=f'Spec "{spec_name}" not found in project {project_name}',
                )
        except RoadmapNotFoundError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to delete spec: {str(e)}')

    def link_loop_to_spec(self, loop_id: str, project_name: str, spec_name: str) -> MCPResponse:
        if not loop_id:
            raise ToolError('Loop ID cannot be empty')
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not spec_name:
            raise ToolError('Spec name cannot be empty')

        try:
            self.state.link_loop_to_spec(loop_id, project_name, spec_name)
            loop_state = self.state.get_loop(loop_id)
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Linked loop {loop_id} to spec "{spec_name}" in project {project_name}',
            )
        except SpecNotFoundError as e:
            raise ResourceError(str(e))
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Failed to link loop to spec: {str(e)}')

    def unlink_loop(self, loop_id: str) -> MCPResponse:
        if not loop_id:
            raise ToolError('Loop ID cannot be empty')

        try:
            result = self.state.unlink_loop(loop_id)
            loop_state = self.state.get_loop(loop_id)
            if result:
                project_name, spec_name = result
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message=f'Unlinked loop {loop_id} from spec "{spec_name}" in project {project_name}',
                )
            else:
                return MCPResponse(
                    id=loop_id, status=loop_state.status, message=f'Loop {loop_id} was not linked to any spec'
                )
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Failed to unlink loop: {str(e)}')


def register_spec_tools(mcp: FastMCP) -> None:
    spec_tools = SpecTools(state_manager)

    @mcp.tool()
    async def store_spec(project_name: str, spec_name: str, spec_markdown: str, ctx: Context) -> str:
        """Store technical specification with automatic versioning.

        Parses markdown content into a TechnicalSpec model and stores it in the
        unified spec storage. Automatically increments iteration and version if
        updating an existing spec.

        Parameters:
        - project_name: Project identifier from .specter/config.json
        - spec_name: Name/phase of the specification
        - spec_markdown: Complete specification in markdown format

        Returns:
        - str: Confirmation message with iteration and version
        """
        await ctx.info(f'Storing spec "{spec_name}" for project {project_name}')
        try:
            result = spec_tools.store_spec(project_name, spec_name, spec_markdown)
            await ctx.info(f'Stored spec "{spec_name}" for project {project_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to store spec: {str(e)}')
            raise

    @mcp.tool()
    async def update_spec(project_name: str, spec_name: str, updated_markdown: str, ctx: Context) -> str:
        """Update existing technical specification while preserving initial state fields.

        Retrieves existing spec, parses updated markdown, and preserves immutable
        initial fields (objectives, scope, dependencies, deliverables). Auto-increments
        iteration and version.

        Parameters:
        - project_name: Project identifier from .specter/config.json
        - spec_name: Name/phase of the specification to update
        - updated_markdown: Complete updated specification in markdown format

        Returns:
        - str: Confirmation message with iteration and version
        """
        await ctx.info(f'Updating spec "{spec_name}" for project {project_name}')
        try:
            result = spec_tools.update_spec(project_name, spec_name, updated_markdown)
            await ctx.info(f'Updated spec "{spec_name}" for project {project_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to update spec: {str(e)}')
            raise

    @mcp.tool()
    async def get_spec_markdown(
        project_name: str | None, spec_name: str | None, loop_id: str | None, ctx: Context
    ) -> MCPResponse:
        """Retrieve specification as markdown.

        Two retrieval modes:
        1. By loop_id: Retrieves spec linked to active refinement loop
        2. By project_name + spec_name: Retrieves spec directly from storage

        Parameters:
        - project_name: Project identifier from .specter/config.json (required if not using loop_id)
        - spec_name: Spec name (required if not using loop_id)
        - loop_id: Loop identifier (alternative to project_name + spec_name)

        Returns:
        - MCPResponse: Contains spec markdown in message field
        """
        await ctx.info('Retrieving spec markdown')
        try:
            result = spec_tools.get_spec_markdown(project_name, spec_name, loop_id)
            await ctx.info('Retrieved spec markdown')
            return result
        except Exception as e:
            await ctx.error(f'Failed to retrieve spec: {str(e)}')
            raise

    @mcp.tool()
    async def list_specs(project_name: str, ctx: Context) -> MCPResponse:
        """List all specifications for a project.

        Parameters:
        - project_name: Project identifier from .specter/config.json

        Returns:
        - MCPResponse: Contains list of spec names in message field
        """
        await ctx.info(f'Listing specs for project {project_name}')
        try:
            result = spec_tools.list_specs(project_name)
            await ctx.info(f'Listed specs for project {project_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to list specs: {str(e)}')
            raise

    @mcp.tool()
    async def resolve_spec_name(project_name: str, partial_name: str, ctx: Context) -> dict:
        """Resolve partial spec name to matching specifications.

        Searches for specs matching the partial name and returns all matches.
        If exactly one match found, returns it as canonical_name.

        Parameters:
        - project_name: Project identifier from .specter/config.json
        - partial_name: Partial or full spec name to search for

        Returns:
        - dict with canonical_name (str|None), matches (list), count (int)
        """
        await ctx.info(f'Resolving spec name: {partial_name} in project {project_name}')

        try:
            canonical, matches = spec_tools.resolve_spec_name(project_name, partial_name)

            result = {
                'canonical_name': canonical,
                'matches': matches,
                'count': len(matches),
            }

            await ctx.info(f'Found {len(matches)} matches')
            return result
        except Exception as e:
            await ctx.error(f'Failed to resolve spec name: {str(e)}')
            raise

    @mcp.tool()
    async def delete_spec(project_name: str, spec_name: str, ctx: Context) -> MCPResponse:
        """Delete a specification from storage.

        Parameters:
        - project_name: Project identifier from .specter/config.json
        - spec_name: Spec name to delete

        Returns:
        - MCPResponse: Contains deletion confirmation
        """
        await ctx.info(f'Deleting spec "{spec_name}" from project {project_name}')
        try:
            result = spec_tools.delete_spec(project_name, spec_name)
            await ctx.info(f'Deleted spec "{spec_name}" from project {project_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to delete spec: {str(e)}')
            raise

    @mcp.tool()
    async def link_loop_to_spec(loop_id: str, project_name: str, spec_name: str, ctx: Context) -> MCPResponse:
        """Link active refinement loop to specification for idempotent iteration.

        Creates temporary mapping allowing agents to retrieve/update specs via loop_id
        during refinement sessions. Enables idempotent spec-architect pattern.

        Parameters:
        - loop_id: Active loop identifier
        - project_name: Project identifier from .specter/config.json
        - spec_name: Spec name to link

        Returns:
        - MCPResponse: Contains linking confirmation
        """
        await ctx.info(f'Linking loop {loop_id} to spec "{spec_name}" in project {project_name}')
        try:
            result = spec_tools.link_loop_to_spec(loop_id, project_name, spec_name)
            await ctx.info(f'Linked loop {loop_id} to spec')
            return result
        except Exception as e:
            await ctx.error(f'Failed to link loop to spec: {str(e)}')
            raise

    @mcp.tool()
    async def unlink_loop(loop_id: str, ctx: Context) -> MCPResponse:
        """Remove loop-to-spec mapping after refinement completion.

        Cleans up temporary mapping when refinement loop completes.

        Parameters:
        - loop_id: Loop identifier to unlink

        Returns:
        - MCPResponse: Contains unlinking confirmation
        """
        await ctx.info(f'Unlinking loop {loop_id}')
        try:
            result = spec_tools.unlink_loop(loop_id)
            await ctx.info(f'Unlinked loop {loop_id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to unlink loop: {str(e)}')
            raise
