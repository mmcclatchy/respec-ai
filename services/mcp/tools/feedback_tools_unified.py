import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from services.models.feedback import CriticFeedback
from services.shared import state_manager
from services.utils.errors import LoopNotFoundError
from services.utils.loop_state import MCPResponse
from services.utils.state_manager import StateManager


logger = logging.getLogger(__name__)


class UnifiedFeedbackTools:
    """Unified feedback management for both critic and user feedback.

    All feedback (critic-generated and user-provided) is stored together
    in chronological order per loop_id. Agents retrieve feedback without
    caring about the source - they just incorporate whatever guidance exists.
    """

    def __init__(self, state: StateManager) -> None:
        self.state = state
        # Store user feedback separately (simple markdown strings)
        # Critic feedback goes into LoopState.feedback_history (structured CriticFeedback objects)
        self._user_feedback: dict[str, list[str]] = {}  # loop_id -> list of feedback
        # Analysis storage for plan-analyst workflow
        self._analysis_storage: dict[str, str] = {}  # loop_id -> analysis

    def store_critic_feedback(self, loop_id: str, feedback_markdown: str) -> MCPResponse:
        """Store structured critic feedback from automated assessment.

        Args:
            loop_id: Loop identifier
            feedback_markdown: CriticFeedback in markdown format

        Returns:
            MCPResponse with confirmation and score
        """
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if not feedback_markdown or not feedback_markdown.strip():
            raise ToolError('Feedback markdown cannot be empty')

        try:
            loop_state = self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        # Parse and validate critic feedback
        feedback = self._parse_and_validate_feedback(feedback_markdown)

        # Add to loop state (updates score, adds to feedback_history)
        loop_state.add_feedback(feedback)

        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message=f'Stored critic feedback for loop {loop_id} (Score: {feedback.overall_score})',
        )

    def store_user_feedback(self, loop_id: str, feedback_markdown: str) -> MCPResponse:
        """Store user-provided feedback during stagnation or user_input status.

        Args:
            loop_id: Loop identifier
            feedback_markdown: User feedback in markdown format

        Returns:
            MCPResponse with confirmation
        """
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if not feedback_markdown or not feedback_markdown.strip():
            raise ToolError('User feedback cannot be empty')

        try:
            loop_state = self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        storage_key = loop_id

        # Initialize user feedback list if needed
        if storage_key not in self._user_feedback:
            self._user_feedback[storage_key] = []

        # Append user feedback (chronological order)
        self._user_feedback[storage_key].append(feedback_markdown)

        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message=f'Stored user feedback for loop {loop_id}',
        )

    def get_feedback(self, loop_id: str, count: int = 2) -> MCPResponse:
        """Get recent feedback (critic + user) for a loop in chronological order.

        Returns combined feedback showing recent iteration progression and user guidance.
        Default retrieves 2 most recent iterations to provide current context plus
        previous iteration for stagnation detection (aligns with <5 points over 2 iterations).

        Args:
            loop_id: Loop identifier
            count: Number of recent critic feedback iterations to retrieve (default: 2)
                   User feedback always included as it's typically sparse

        Returns:
            MCPResponse with combined feedback markdown or empty message
        """
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if count <= 0:
            raise ToolError('Count must be a positive integer')

        try:
            loop_state = self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        storage_key = loop_id

        # Get recent critic feedback from loop state (limited by count)
        critic_feedback_list = loop_state.get_recent_feedback(count=count)

        # Get user feedback (all of it - typically sparse, high-value signal)
        user_feedback_list = self._user_feedback.get(storage_key, [])

        # Build combined feedback markdown
        if not critic_feedback_list and not user_feedback_list:
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message='No feedback available for this loop',
            )

        feedback_parts = []

        # Add critic feedback history
        if critic_feedback_list:
            feedback_parts.append('# Critic Feedback History\n')
            for i, critic_feedback in enumerate(critic_feedback_list, 1):
                logger.debug(
                    f'get_feedback: formatting iteration {i} with score={critic_feedback.overall_score}, '
                    f'iteration={critic_feedback.iteration}'
                )
                feedback_parts.append(f'## Iteration {i} - Score: {critic_feedback.overall_score}\n')
                feedback_parts.append(f'{critic_feedback.assessment_summary}\n')
                if critic_feedback.key_issues:
                    feedback_parts.append('**Key Issues:**')
                    for issue in critic_feedback.key_issues:
                        feedback_parts.append(f'- {issue}')
                    feedback_parts.append('')
                if critic_feedback.recommendations:
                    feedback_parts.append('**Recommendations:**')
                    for rec in critic_feedback.recommendations:
                        feedback_parts.append(f'- {rec}')
                    feedback_parts.append('')
                feedback_parts.append('---\n')

        # Add user feedback
        if user_feedback_list:
            feedback_parts.append('# User Feedback\n')
            for i, user_feedback in enumerate(user_feedback_list, 1):
                feedback_parts.append(f'## User Input {i}\n')
                feedback_parts.append(f'{user_feedback}\n')
                feedback_parts.append('---\n')

        message = '\n'.join(feedback_parts)
        return MCPResponse(id=loop_id, status=loop_state.status, message=message)

    def store_current_analysis(self, loop_id: str, analysis: str) -> MCPResponse:
        """Store current analysis (used by plan-analyst workflow).

        Args:
            loop_id: Loop identifier
            analysis: Structured analysis in markdown format

        Returns:
            MCPResponse with confirmation
        """
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if not analysis or not analysis.strip():
            raise ToolError('Analysis cannot be empty')

        try:
            loop_state = self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        storage_key = loop_id
        self._analysis_storage[storage_key] = analysis
        return MCPResponse(id=loop_id, status=loop_state.status, message=f'Stored analysis for loop {loop_id}')

    def get_previous_analysis(self, loop_id: str) -> MCPResponse:
        """Get previous analysis (used by plan-analyst workflow).

        Args:
            loop_id: Loop identifier

        Returns:
            MCPResponse with analysis content or empty message
        """
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')

        try:
            loop_state = self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        storage_key = loop_id
        analysis = self._analysis_storage.get(storage_key, '')
        if analysis:
            message = f'Previous analysis for loop {loop_id}:\n\n{analysis}'
        else:
            message = f'No previous analysis found for loop {loop_id}'

        return MCPResponse(id=loop_id, status=loop_state.status, message=message)

    def _parse_and_validate_feedback(self, feedback_markdown: str) -> CriticFeedback:
        try:
            feedback = CriticFeedback.parse_markdown(feedback_markdown)
        except Exception as e:
            raise ToolError(f'Failed to parse feedback markdown: {str(e)}')

        # Validation checks - look for template placeholders, not legitimate use of "unknown"
        if 'Critic Feedback: UNKNOWN' in feedback_markdown or '# Critic Feedback: UNKNOWN' in feedback_markdown:
            raise ToolError('Feedback must specify a valid critic agent')
        if '# Critic Feedback:' not in feedback_markdown:
            raise ToolError('Feedback missing critic feedback header')
        if (
            feedback.loop_id == 'unknown'
            and feedback.overall_score == 0
            and feedback.assessment_summary == 'Assessment Summary not provided'
        ):
            raise ToolError('Feedback markdown structure is invalid')

        return feedback


def register_unified_feedback_tools(mcp: FastMCP) -> None:
    feedback_tools = UnifiedFeedbackTools(state_manager)

    @mcp.tool()
    async def store_critic_feedback(loop_id: str, feedback_markdown: str, ctx: Context) -> MCPResponse:
        """Store critic feedback from automated assessment agents.

        Parses structured markdown into CriticFeedback model and stores in LoopState.
        Used by all critic agents (build-critic, plan-critic, analyst-critic, etc.).

        Parameters:
        - loop_id: Loop identifier
        - feedback_markdown: CriticFeedback in structured markdown format

        Returns:
        - MCPResponse: Contains loop_id, status, confirmation with score
        """
        await ctx.info(f'Storing critic feedback for loop {loop_id}')
        try:
            result = feedback_tools.store_critic_feedback(loop_id, feedback_markdown)
            await ctx.info(f'Stored critic feedback for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to store critic feedback: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ToolError(f'Unexpected error storing critic feedback: {str(e)}')

    @mcp.tool()
    async def store_user_feedback(loop_id: str, feedback_markdown: str, ctx: Context) -> MCPResponse:
        """Store user-provided feedback during stagnation or user_input status.

        Stores free-form markdown feedback from users when refinement stagnates
        or manual guidance is needed. Agents retrieve and incorporate this alongside
        critic feedback in subsequent iterations.

        Parameters:
        - loop_id: Loop identifier
        - feedback_markdown: User feedback in markdown format

        Returns:
        - MCPResponse: Contains loop_id, status, confirmation
        """
        await ctx.info(f'Storing user feedback for loop {loop_id}')
        try:
            result = feedback_tools.store_user_feedback(loop_id, feedback_markdown)
            await ctx.info(f'Stored user feedback for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to store user feedback: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ToolError(f'Unexpected error storing user feedback: {str(e)}')

    @mcp.tool()
    async def get_feedback(loop_id: str, count: int, ctx: Context) -> MCPResponse:
        """Get recent feedback (critic + user) for a loop in chronological order.

        Returns combined feedback showing recent iteration progression and user guidance.
        Default retrieves 2 most recent iterations for stagnation detection context
        (current + previous to see if <5 points improvement).

        Parameters:
        - loop_id: Loop identifier
        - count: Number of recent critic feedback iterations to retrieve (default: 2)
                 Agents can request more if needed for broader context

        Returns:
        - MCPResponse: Contains recent feedback in chronological markdown format
        """
        await ctx.info(f'Retrieving {count} recent feedback(s) for loop {loop_id}')
        try:
            result = feedback_tools.get_feedback(loop_id, count)
            await ctx.info(f'Retrieved {count} feedback(s) for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to retrieve feedback: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ResourceError(f'Feedback unavailable for loop {loop_id}: {str(e)}')

    @mcp.tool()
    async def store_current_analysis(loop_id: str, analysis: str, ctx: Context) -> MCPResponse:
        await ctx.info(f'Storing analysis for loop {loop_id}')
        try:
            result = feedback_tools.store_current_analysis(loop_id, analysis)
            await ctx.info(f'Stored analysis for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to store analysis: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ToolError(f'Unexpected error storing analysis: {str(e)}')

    @mcp.tool()
    async def get_previous_analysis(loop_id: str, ctx: Context) -> MCPResponse:
        await ctx.info(f'Retrieving previous analysis for loop {loop_id}')
        try:
            result = feedback_tools.get_previous_analysis(loop_id)
            await ctx.info(f'Retrieved analysis for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to retrieve analysis: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ResourceError(f'Analysis unavailable for loop {loop_id}: {str(e)}')
