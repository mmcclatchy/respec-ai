from fastmcp import Context, FastMCP
from src.shared import state_manager
from src.utils.enums import LoopType
from src.utils.errors import LoopAlreadyExistsError, LoopNotFoundError, LoopStateError, LoopValidationError
from src.utils.loop_state import LoopState, MCPResponse
from src.utils.state_manager import StateManager


class LoopTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def initialize_refinement_loop(self, project_name: str, loop_type: str) -> MCPResponse:
        try:
            loop_type_enum = LoopType(loop_type)
            loop_state = LoopState(loop_type=loop_type_enum)
            await self.state.add_loop(loop_state, project_name)
            return loop_state.mcp_response
        except ValueError:
            valid_types = {'plan', 'spec', 'build_plan', 'build_code'}
            raise LoopValidationError('loop_type', f'Must be one of {valid_types}')
        except LoopValidationError:
            raise
        except LoopAlreadyExistsError as e:
            raise LoopStateError('new', 'initialization', f'Failed to create loop: {str(e)}')
        except Exception as e:
            raise LoopStateError('new', 'initialization', f'Unexpected error: {str(e)}')

    async def get_loop_status(self, loop_id: str) -> MCPResponse:
        try:
            return await self.state.get_loop_status(loop_id)
        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'status_retrieval', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'status_retrieval', f'Unexpected error: {str(e)}')

    async def list_active_loops(self, project_name: str) -> list[MCPResponse]:
        try:
            return await self.state.list_active_loops(project_name)
        except Exception as e:
            raise LoopStateError('all', 'list_retrieval', f'Failed to retrieve loop list: {str(e)}')

    async def decide_loop_next_action(self, loop_id: str, current_score: int) -> MCPResponse:
        """MCP tool to decide the next action for a refinement loop.

        This is the main MCP tool interface that external agents will call
        to determine whether to continue refining, complete the loop, or
        request user input based on quality scores and iteration count.
        """
        try:
            if not (0 <= current_score <= 100):
                raise LoopValidationError('score', 'Must be between 0 and 100')
            return await self.state.decide_loop_next_action(loop_id, current_score)
        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'decision', 'Loop does not exist')
        except LoopValidationError:
            raise  # Re-raise validation errors as-is
        except Exception as e:
            raise LoopStateError(loop_id, 'decision', f'Unexpected error: {str(e)}')

    async def get_previous_objective_feedback(self, loop_id: str) -> MCPResponse:
        try:
            return await self.state.get_objective_feedback(loop_id)
        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'feedback_retrieval', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'feedback_retrieval', f'Unexpected error: {str(e)}')

    async def store_current_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse:
        try:
            return await self.state.store_objective_feedback(loop_id, feedback)
        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'feedback_storage', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'feedback_storage', f'Unexpected error: {str(e)}')

    async def get_loop_feedback_summary(self, loop_id: str) -> MCPResponse:
        """Get structured feedback summary for loop decision making.

        Provides feedback metrics and trends to support intelligent
        loop progression decisions. Returns score progression,
        feedback count, and recent assessment summaries.
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

            # Build feedback summary for decision context
            feedback_count = len(loop_state.feedback_history)
            current_score = loop_state.current_score
            score_trend = self._calculate_score_trend(loop_state.score_history)

            recent_summaries = [f'Iteration {fb.iteration}: {fb.assessment_summary}' for fb in recent_feedback]

            summary_message = (
                f'Feedback Summary: {feedback_count} total assessments, '
                f'current score {current_score}, trend: {score_trend}. '
                f'Recent: {"; ".join(recent_summaries[-2:])}'
            )

            return MCPResponse(id=loop_id, status=loop_state.status, message=summary_message)

        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'feedback_summary', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'feedback_summary', f'Unexpected error: {str(e)}')

    async def get_loop_improvement_analysis(self, loop_id: str) -> MCPResponse:
        """Analyze improvement patterns from structured feedback.

        Examines feedback history to identify improvement trends,
        recurring issues, and recommendation patterns. Supports
        intelligent refinement strategy decisions.
        """
        try:
            loop_state = await self.state.get_loop(loop_id)
            feedback_history = loop_state.feedback_history

            if len(feedback_history) < 2:
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message='Insufficient feedback history for improvement analysis - need at least 2 assessments',
                )

            # Analyze improvement patterns
            score_improvements = []
            for i in range(1, len(feedback_history)):
                score_improvements.append(feedback_history[i].overall_score - feedback_history[i - 1].overall_score)

            avg_improvement = sum(score_improvements) / len(score_improvements)
            last_improvement = score_improvements[-1] if score_improvements else 0

            # Identify recurring issues
            all_issues = [issue for fb in feedback_history for issue in fb.key_issues]
            issue_counts: dict[str, int] = {}
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

            recurring_issues = [issue for issue, count in issue_counts.items() if count >= 2]

            # Build analysis message
            trend_desc = 'improving' if avg_improvement > 0 else 'declining' if avg_improvement < 0 else 'stable'
            analysis_message = (
                f'Improvement Analysis: {trend_desc} trend (avg: {avg_improvement:+.1f} points), '
                f'last change: {last_improvement:+d} points. '
            )

            if recurring_issues:
                analysis_message += f'Recurring issues: {", ".join(recurring_issues[:3])}. '
            else:
                analysis_message += 'No recurring issues identified. '

            return MCPResponse(id=loop_id, status=loop_state.status, message=analysis_message)

        except LoopNotFoundError:
            raise LoopStateError(loop_id, 'improvement_analysis', 'Loop does not exist')
        except Exception as e:
            raise LoopStateError(loop_id, 'improvement_analysis', f'Unexpected error: {str(e)}')

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
    @mcp.tool()
    async def decide_loop_next_action(loop_id: str, current_score: int, ctx: Context) -> MCPResponse:
        """Decide next action for refinement loop progression.

        This MCP tool implements the core decision logic for quality-driven
        refinement loops. It analyzes current quality scores, improvement trends,
        and iteration counts to determine whether to continue refining content,
        complete the loop, or escalate to human input.

        Parameters:
        - loop_id: Unique identifier of the loop to process
        - current_score: Quality score from 0-100 for current iteration

        Returns:
        - MCPResponse: Contains loop_id and status ('completed', 'refine', 'user_input')
        """
        await ctx.info(f'Processing decision for loop {loop_id} with score {current_score}')
        result = await loop_tools.decide_loop_next_action(loop_id, current_score)
        await ctx.info(f'Decision result for loop {loop_id}: {result.status}')
        return result

    @mcp.tool()
    async def initialize_refinement_loop(project_name: str, loop_type: str, ctx: Context) -> MCPResponse:
        """Initialize a new refinement loop.

        Creates a new refinement loop session.
        Returns loop ID for tracking and managing the loop state throughout
        the refinement process.

        Parameters:
        - project_name: Name of the project (from .respec-ai/config.json)
        - loop_type: One of 'plan', 'spec', 'build_plan', 'build_code'

        Returns:
        - MCPResponse: Contains loop_id and status ('initialized')
        """
        await ctx.info(f'Initializing new {loop_type} loop for {project_name}')
        result = await loop_tools.initialize_refinement_loop(project_name, loop_type)
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
        result = await loop_tools.get_loop_status(loop_id)
        await ctx.info(f'Retrieved status for loop {loop_id}: {result.status}')
        return result

    @mcp.tool()
    async def list_active_loops(project_name: str, ctx: Context) -> list[MCPResponse]:
        """List all currently active refinement loops.

        Returns summary information for all active loops in the current
        session. Useful for managing multiple concurrent refinement processes.

        Parameters:
        - project_name: Name of the project (from .respec-ai/config.json)

        Returns:
        - list[MCPResponse]: List of active loops with their current status
        """
        await ctx.info(f'Retrieving list of active loops for {project_name}')
        result = await loop_tools.list_active_loops(project_name)
        await ctx.info(f'Found {len(result)} active loops')
        return result

    @mcp.tool()
    async def get_previous_objective_feedback(loop_id: str, ctx: Context) -> MCPResponse:
        """Retrieve previous objective validation feedback for analyst-critic.

        Returns stored feedback from previous validation cycles to enable
        iterative improvement tracking and consistency assessment.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains previous feedback data with dimension scores and recommendations
        """
        await ctx.info(f'Retrieving previous objective feedback for loop {loop_id}')
        result = await loop_tools.get_previous_objective_feedback(loop_id)
        await ctx.info(f'Retrieved objective feedback for loop {loop_id}')
        return result

    @mcp.tool()
    async def store_current_objective_feedback(loop_id: str, feedback: str, ctx: Context) -> MCPResponse:
        """Store current objective validation feedback for analyst-critic.

        Persists validation feedback including dimension scores, specific findings,
        and improvement recommendations for future refinement cycles.

        Parameters:
        - loop_id: Unique identifier of the loop
        - feedback: Complete validation feedback with scores and recommendations

        Returns:
        - MCPResponse: Confirmation of successful storage
        """
        await ctx.info(f'Storing objective feedback for loop {loop_id}')
        result = await loop_tools.store_current_objective_feedback(loop_id, feedback)
        await ctx.info(f'Stored objective feedback for loop {loop_id}')
        return result

    @mcp.tool()
    async def get_loop_feedback_summary(loop_id: str, ctx: Context) -> MCPResponse:
        """Get structured feedback summary for loop decision making.

        Provides feedback metrics and trends to support intelligent
        loop progression decisions. Returns score progression,
        feedback count, and recent assessment summaries.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains feedback summary with metrics and trends
        """
        await ctx.info(f'Retrieving feedback summary for loop {loop_id}')
        result = await loop_tools.get_loop_feedback_summary(loop_id)
        await ctx.info(f'Retrieved feedback summary for loop {loop_id}')
        return result

    @mcp.tool()
    async def get_loop_improvement_analysis(loop_id: str, ctx: Context) -> MCPResponse:
        """Analyze improvement patterns from structured feedback.

        Examines feedback history to identify improvement trends,
        recurring issues, and recommendation patterns. Supports
        intelligent refinement strategy decisions.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains improvement analysis with trends and patterns
        """
        await ctx.info(f'Retrieving improvement analysis for loop {loop_id}')
        result = await loop_tools.get_loop_improvement_analysis(loop_id)
        await ctx.info(f'Retrieved improvement analysis for loop {loop_id}')
        return result


loop_tools = LoopTools(state_manager)
