from fastmcp import Context, FastMCP

from src.utils.enums import LoopType
from src.utils.errors import LoopAlreadyExistsError, LoopNotFoundError, LoopStateError, LoopValidationError
from src.utils.loop_state import LoopState, MCPResponse
from src.utils.state_manager import StateManager


class LoopTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def initialize_refinement_loop(self, plan_name: str, loop_type: str) -> MCPResponse:
        try:
            loop_type_enum = LoopType(loop_type)
            loop_state = LoopState(loop_type=loop_type_enum)
            await self.state.add_loop(loop_state, plan_name)
            return loop_state.mcp_response
        except ValueError:
            valid_types = {'plan', 'roadmap', 'phase', 'task', 'analyst'}
            raise LoopValidationError('loop_type', f'Must be one of {valid_types}')
        except LoopValidationError:
            raise
        except LoopAlreadyExistsError as e:
            raise LoopStateError(
                'new',
                'initialization',
                f'Failed to create loop: {str(e)}. '
                f'A previous plan session may still exist. '
                f'To start fresh, run: respec-ai db delete-plan {plan_name}',
            )
        except Exception as e:
            raise LoopStateError('new', 'initialization', f'Unexpected error: {str(e)}')

    async def get_loop_status(self, loop_id: str) -> MCPResponse:
        try:
            return await self.state.get_loop_status(loop_id)
        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'status_retrieval', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'status_retrieval', f'Unexpected error: {str(e)}')

    async def list_active_loops(self, plan_name: str) -> list[MCPResponse]:
        try:
            return await self.state.list_active_loops(plan_name)
        except Exception as e:
            raise LoopStateError('all', 'list_retrieval', f'Failed to retrieve loop list: {str(e)}')

    async def decide_loop_next_action(self, loop_id: str) -> MCPResponse:
        """MCP tool to decide the next action for a refinement loop.

        This is the main MCP tool interface that external agents will call
        to determine whether to continue refining, complete the loop, or
        request user input based on quality scores and iteration count.

        The score is retrieved internally from the latest critic feedback
        stored in the loop state, implementing the context-optimized pattern
        where commands only pass loop_id and MCP handles data retrieval.
        """
        try:
            return await self.state.decide_loop_next_action(loop_id)
        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'decision', 'Loop does not exist')
        except ValueError as e:
            raise LoopStateError(loop_id, 'decision', str(e))
        except Exception as e:
            raise LoopStateError(loop_id, 'decision', f'Unexpected error: {str(e)}')

    async def get_loop_feedback_summary(self, loop_id: str) -> MCPResponse:
        """Get structured feedback summary with improvement analysis for loop decision making.

        Provides feedback metrics, trends, and improvement patterns to support intelligent
        loop progression decisions. Returns score progression, feedback count, recent
        assessment summaries, and recurring issue analysis.
        """
        try:
            loop_state = await self.state.get_loop(loop_id)
            recent_feedback = loop_state.get_recent_feedback(3)

            if not recent_feedback:
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message='No feedback available - loop ready for first assessment',
                )

            feedback_count = len(loop_state.feedback_history)
            current_score = loop_state.current_score
            score_trend = self._calculate_score_trend(loop_state.score_history)
            recent_summaries = [f'Iteration {fb.iteration}: {fb.assessment_summary}' for fb in recent_feedback]

            summary_message = (
                f'Feedback Summary: {feedback_count} total assessments, '
                f'current score {current_score}, trend: {score_trend}. '
                f'Recent: {"; ".join(recent_summaries[-2:])}. '
            )

            feedback_history = loop_state.feedback_history
            if len(feedback_history) >= 2:
                score_improvements = []
                for i in range(1, len(feedback_history)):
                    score_improvements.append(feedback_history[i].overall_score - feedback_history[i - 1].overall_score)

                avg_improvement = sum(score_improvements) / len(score_improvements)
                last_improvement = score_improvements[-1] if score_improvements else 0

                all_issues = [issue for fb in feedback_history for issue in fb.key_issues]
                issue_counts: dict[str, int] = {}
                for issue in all_issues:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
                recurring_issues = [issue for issue, count in issue_counts.items() if count >= 2]

                trend_desc = 'improving' if avg_improvement > 0 else 'declining' if avg_improvement < 0 else 'stable'
                summary_message += (
                    f'Improvement: {trend_desc} (avg: {avg_improvement:+.1f} points, '
                    f'last: {last_improvement:+d} points). '
                )
                if recurring_issues:
                    summary_message += f'Recurring issues: {", ".join(recurring_issues[:3])}'
                else:
                    summary_message += 'No recurring issues'

            return MCPResponse(id=loop_id, status=loop_state.status, message=summary_message)

        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'feedback_summary', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'feedback_summary', f'Unexpected error: {str(e)}')

    def _calculate_score_trend(self, score_history: list[int]) -> str:
        if len(score_history) < 2:
            return 'insufficient data'

        recent_scores = score_history[-3:] if len(score_history) >= 3 else score_history
        if len(recent_scores) < 2:
            return 'insufficient data'

        total_change = recent_scores[-1] - recent_scores[0]
        if total_change > 5:
            return 'improving'
        elif total_change < -5:
            return 'declining'
        else:
            return 'stable'


def register_loop_tools(mcp: FastMCP) -> None:
    _tools: LoopTools | None = None

    def _get_tools(ctx: Context) -> LoopTools:
        nonlocal _tools
        if _tools is None:
            _tools = LoopTools(ctx.lifespan_context['state_manager'])
        return _tools

    @mcp.tool()
    async def decide_loop_next_action(loop_id: str, ctx: Context) -> MCPResponse:
        """Decide next action for refinement loop progression.

        This MCP tool implements the core decision logic for quality-driven
        refinement loops. It retrieves the latest quality score from stored
        critic feedback, analyzes improvement trends and iteration counts to
        determine whether to continue refining content, complete the loop,
        or escalate to human input.

        Context-Optimized Pattern: The score is extracted internally from the
        loop's feedback history. Commands only need to pass loop_id, reducing
        context usage by 99% compared to passing scores as parameters.

        Parameters:
        - loop_id: Unique identifier of the loop to process

        Returns:
        - MCPResponse: Contains loop_id and status ('completed', 'refine', 'user_input')
        """
        await ctx.info(f'Processing decision for loop {loop_id} (score retrieved from feedback internally)')
        result = await _get_tools(ctx).decide_loop_next_action(loop_id)
        await ctx.info(f'Decision result for loop {loop_id}: {result.status}')
        return result

    @mcp.tool()
    async def initialize_refinement_loop(plan_name: str, loop_type: str, ctx: Context) -> MCPResponse:
        """Initialize a new refinement loop.

        Creates a new refinement loop session.
        Returns loop ID for tracking and managing the loop state throughout
        the refinement process.

        Parameters:
        - plan_name: Name of the project (from .respec-ai/config.json)
        - loop_type: One of 'plan', 'roadmap', 'phase', 'task', 'analyst'

        Returns:
        - MCPResponse: Contains loop_id and status ('initialized')
        """
        await ctx.info(f'Initializing new {loop_type} loop for {plan_name}')
        result = await _get_tools(ctx).initialize_refinement_loop(plan_name, loop_type)
        await ctx.info(f'Created {loop_type} loop with ID: {result.id}')
        return result

    @mcp.tool()
    async def get_loop_status(loop_id: str, ctx: Context) -> MCPResponse:
        """Get current status and history of a loop.

        Returns complete loop information including current status,
        iteration count, score history, and metadata.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Complete loop state with all metadata and history
        """
        await ctx.info(f'Retrieving status for loop {loop_id}')
        result = await _get_tools(ctx).get_loop_status(loop_id)
        await ctx.info(f'Retrieved status for loop {loop_id}: {result.status}')
        return result

    @mcp.tool()
    async def list_active_loops(plan_name: str, ctx: Context) -> list[MCPResponse]:
        """List all currently active refinement loops.

        Returns summary information for all active loops in the current
        session. Useful for managing multiple concurrent refinement processes.

        Parameters:
        - plan_name: Name of the project (from .respec-ai/config.json)

        Returns:
        - list[MCPResponse]: List of active loops with their current status
        """
        await ctx.info(f'Retrieving list of active loops for {plan_name}')
        result = await _get_tools(ctx).list_active_loops(plan_name)
        await ctx.info(f'Found {len(result)} active loops')
        return result

    @mcp.tool()
    async def get_loop_feedback_summary(loop_id: str, ctx: Context) -> MCPResponse:
        """Get structured feedback summary with improvement analysis for loop decision making.

        Provides feedback metrics, trends, and improvement patterns to support intelligent
        loop progression decisions. Returns score progression, feedback count, recent
        assessment summaries, recurring issues, and improvement trends.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains feedback summary with metrics, trends, and improvement analysis
        """
        await ctx.info(f'Retrieving feedback summary for loop {loop_id}')
        result = await _get_tools(ctx).get_loop_feedback_summary(loop_id)
        await ctx.info(f'Retrieved feedback summary for loop {loop_id}')
        return result
