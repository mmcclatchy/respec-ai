import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from src.models.enums import CriticAgent, Priority
from src.models.feedback import CriticFeedback, ReviewFinding, ReviewerResult
from src.utils.errors import LoopNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


logger = logging.getLogger(__name__)


class UnifiedFeedbackTools:
    """Unified feedback management for both critic and user feedback.

    All feedback (critic-generated and user-provided) is stored together
    in chronological order per loop_id. Agents retrieve feedback without
    caring about the source - they just incorporate whatever guidance exists.
    """

    def __init__(self, state: StateManager) -> None:
        self.state = state
        self._phase1_core_weights: dict[CriticAgent, float] = {
            CriticAgent.AUTOMATED_QUALITY_CHECKER: 0.30,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER: 0.35,
            CriticAgent.CODE_QUALITY_REVIEWER: 0.15,
        }
        self._phase1_specialists: set[CriticAgent] = {
            CriticAgent.FRONTEND_REVIEWER,
            CriticAgent.BACKEND_API_REVIEWER,
            CriticAgent.DATABASE_REVIEWER,
            CriticAgent.INFRASTRUCTURE_REVIEWER,
        }
        self._phase1_review_universe: list[CriticAgent] = [
            CriticAgent.AUTOMATED_QUALITY_CHECKER,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER,
            CriticAgent.CODE_QUALITY_REVIEWER,
            CriticAgent.FRONTEND_REVIEWER,
            CriticAgent.BACKEND_API_REVIEWER,
            CriticAgent.DATABASE_REVIEWER,
            CriticAgent.INFRASTRUCTURE_REVIEWER,
        ]
        self._phase2_review_universe: list[CriticAgent] = [CriticAgent.CODING_STANDARDS_REVIEWER]

    async def store_critic_feedback(self, loop_id: str, feedback_markdown: str) -> MCPResponse:
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
            loop_state = await self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        # Parse and validate critic feedback
        feedback = self._parse_and_validate_feedback(feedback_markdown)

        # Add to loop state (updates score, adds to feedback_history)
        loop_state.upsert_feedback(feedback)
        await self.state.save_loop(loop_state)

        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message=f'Stored critic feedback for loop {loop_id} (Score: {feedback.overall_score})',
        )

    async def store_user_feedback(self, loop_id: str, feedback_markdown: str) -> MCPResponse:
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
            loop_status = await self.state.get_loop_status(loop_id)
            await self.state.append_user_feedback(loop_id, feedback_markdown)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        return MCPResponse(
            id=loop_id,
            status=loop_status.status,
            message=f'Stored user feedback for loop {loop_id}',
        )

    async def get_feedback(self, loop_id: str, count: int = 2) -> MCPResponse:
        """Get recent feedback (critic + user) for a loop in chronological order.

        Returns combined feedback showing recent iteration progression and user guidance.
        Default retrieves 2 most recent iterations to provide current context plus
        previous iteration for stagnation detection.

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
            loop_state = await self.state.get_loop(loop_id)
            user_feedback_list = await self.state.list_user_feedback(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        # Get recent critic feedback from loop state (limited by count)
        critic_feedback_list = loop_state.get_recent_feedback(count=count)

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

    async def store_current_analysis(self, loop_id: str, analysis: str) -> MCPResponse:
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
            loop_status = await self.state.get_loop_status(loop_id)
            await self.state.upsert_loop_analysis(loop_id, analysis)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        return MCPResponse(id=loop_id, status=loop_status.status, message=f'Stored analysis for loop {loop_id}')

    async def get_previous_analysis(self, loop_id: str) -> MCPResponse:
        """Get previous analysis (used by plan-analyst workflow).

        Args:
            loop_id: Loop identifier

        Returns:
            MCPResponse with analysis content or empty message
        """
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')

        try:
            loop_status = await self.state.get_loop_status(loop_id)
            analysis = await self.state.get_loop_analysis(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        if analysis:
            message = f'Previous analysis for loop {loop_id}:\n\n{analysis}'
        else:
            message = f'No previous analysis found for loop {loop_id}'

        return MCPResponse(id=loop_id, status=loop_status.status, message=message)

    async def store_reviewer_result(
        self,
        loop_id: str,
        review_iteration: int,
        reviewer_name: str,
        feedback_markdown: str,
        score: int,
        blockers: list[str],
        findings: list[dict[str, str]],
    ) -> MCPResponse:
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if review_iteration < 1:
            raise ToolError('review_iteration must be >= 1')
        if not reviewer_name or not reviewer_name.strip():
            raise ToolError('reviewer_name cannot be empty')
        if not feedback_markdown or not feedback_markdown.strip():
            raise ToolError('feedback_markdown cannot be empty')

        try:
            loop_state = await self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        review_findings = [
            ReviewFinding(
                priority=Priority(item['priority']),
                feedback=item['feedback'],
            )
            for item in findings
        ]
        reviewer_result = ReviewerResult(
            loop_id=loop_id,
            review_iteration=review_iteration,
            reviewer_name=self._parse_reviewer_name(reviewer_name),
            feedback_markdown=feedback_markdown,
            score=score,
            blockers=blockers or [],
            findings=review_findings,
        )
        await self.state.upsert_reviewer_result(reviewer_result)
        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message=(
                f'Stored reviewer result for {reviewer_result.reviewer_name.value} '
                f'(iteration={review_iteration}, score={reviewer_result.score})'
            ),
        )

    async def consolidate_review_cycle(
        self,
        loop_id: str,
        review_iteration: int,
        active_reviewers: list[str],
    ) -> MCPResponse:
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if review_iteration < 1:
            raise ToolError('review_iteration must be >= 1')
        if not active_reviewers:
            raise ToolError('active_reviewers must not be empty')

        try:
            loop_state = await self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        active_critic_agents = [self._parse_reviewer_name(name) for name in active_reviewers]
        stored_results = await self.state.list_reviewer_results(loop_id, review_iteration)
        results_by_reviewer = {result.reviewer_name: result for result in stored_results}

        missing_reviewers = [name for name in active_critic_agents if name not in results_by_reviewer]
        if missing_reviewers:
            missing = ', '.join(name.value for name in missing_reviewers)
            raise ToolError(f'Cannot consolidate review cycle: missing reviewer submissions: {missing}')

        is_phase2 = active_critic_agents == [CriticAgent.CODING_STANDARDS_REVIEWER]
        universe = self._phase2_review_universe if is_phase2 else self._phase1_review_universe

        active_results = [results_by_reviewer[name] for name in active_critic_agents]
        overall_score = (
            self._compute_phase2_score(active_results) if is_phase2 else self._compute_phase1_score(active_results)
        )

        all_blockers = [
            f'[{result.reviewer_name.value}] {blocker}'
            for result in active_results
            for blocker in result.blockers
            if blocker.strip()
        ]
        findings_by_priority: dict[Priority, list[str]] = {
            Priority.P0: [],
            Priority.P1: [],
            Priority.P2: [],
            Priority.P3: [],
        }
        for result in active_results:
            for finding in result.findings:
                findings_by_priority[finding.priority].append(f'[{result.reviewer_name.value}] {finding.feedback}')

        blocker_active = bool(all_blockers)
        summary = (
            f'Consolidated {len(active_results)} reviewer result(s) for iteration {review_iteration}. '
            f'Composite score={overall_score}/100. '
            + ('[BLOCKING] Active blockers detected.' if blocker_active else 'No active blockers detected.')
        )
        if blocker_active:
            summary += f' Blockers: {len(all_blockers)}'

        issues: list[str] = []
        for priority in (Priority.P0, Priority.P1, Priority.P2, Priority.P3):
            for item in findings_by_priority[priority]:
                issues.append(f'[Severity:{priority.value}] {item}')
        for blocker in all_blockers:
            issues.append(f'[BLOCKING] {blocker}')

        recommendations: list[str] = []
        if blocker_active:
            recommendations.append('[Priority:P0] Resolve all blocking findings before completion.')
        recommendations.append('Address P0/P1 findings first, then rerun review cycle.')

        detail_lines = ['### Reviewer Results', '']
        for reviewer in universe:
            result = results_by_reviewer.get(reviewer)
            if result:
                detail_lines.append(f'#### {reviewer.value}')
                detail_lines.append(f'- Score: {result.score}/100')
                if result.blockers:
                    detail_lines.append('- Blockers:')
                    detail_lines.extend([f'  - {blocker}' for blocker in result.blockers])
                else:
                    detail_lines.append('- Blockers: none')
                detail_lines.append('')
                detail_lines.append(result.feedback_markdown)
                detail_lines.append('')
            else:
                detail_lines.append(f'#### {reviewer.value}')
                detail_lines.append('- Not invoked for this work.')
                detail_lines.append('')

        feedback = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.CODING_STANDARDS_REVIEWER if is_phase2 else CriticAgent.REVIEW_CONSOLIDATOR,
            iteration=review_iteration,
            overall_score=overall_score,
            assessment_summary=summary,
            detailed_feedback='\n'.join(detail_lines).strip(),
            key_issues=issues[:50],
            recommendations=recommendations,
        )
        loop_state.upsert_feedback(feedback)
        await self.state.save_loop(loop_state)

        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            current_score=overall_score,
            iteration=review_iteration,
            message=f'Consolidated review cycle for loop {loop_id} iteration {review_iteration}',
        )

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

    def _compute_phase1_score(self, active_results: list[ReviewerResult]) -> int:
        score_by_reviewer = {result.reviewer_name: result.score for result in active_results}
        core_weights = dict(self._phase1_core_weights)

        specialist_weights: dict[CriticAgent, float] = {}
        active_specialists = [reviewer for reviewer in self._phase1_specialists if reviewer in score_by_reviewer]
        if active_specialists:
            per_specialist_weight = 0.20 / len(active_specialists)
            specialist_weights = {reviewer: per_specialist_weight for reviewer in active_specialists}
        else:
            # Re-normalize core reviewers when no specialists are active.
            core_weight_total = sum(core_weights.values())
            specialist_weights = {}
            core_weights = {reviewer: weight / core_weight_total for reviewer, weight in core_weights.items()}

        weighted_total = 0.0
        for reviewer, weight in core_weights.items():
            if reviewer in score_by_reviewer:
                weighted_total += score_by_reviewer[reviewer] * weight
        for reviewer, weight in specialist_weights.items():
            weighted_total += score_by_reviewer[reviewer] * weight
        return int(round(weighted_total))

    def _compute_phase2_score(self, active_results: list[ReviewerResult]) -> int:
        if not active_results:
            return 0
        return int(round(sum(result.score for result in active_results) / len(active_results)))

    def _parse_reviewer_name(self, reviewer_name: str) -> CriticAgent:
        normalized = reviewer_name.strip()
        for critic in CriticAgent:
            if critic.value == normalized:
                return critic
        raise ToolError(f'Unknown reviewer_name: {reviewer_name}')


def register_unified_feedback_tools(mcp: FastMCP) -> None:
    _tools: UnifiedFeedbackTools | None = None

    def _get_tools(ctx: Context) -> UnifiedFeedbackTools:
        nonlocal _tools
        if _tools is None:
            _tools = UnifiedFeedbackTools(ctx.lifespan_context['state_manager'])
        return _tools

    @mcp.tool()
    async def store_reviewer_result(
        loop_id: str,
        review_iteration: int,
        reviewer_name: str,
        feedback_markdown: str,
        score: int,
        blockers: list[str],
        findings: list[dict[str, str]],
        ctx: Context,
    ) -> MCPResponse:
        """Store a structured reviewer result for deterministic review consolidation.

        Parameters:
        - loop_id: Loop identifier
        - review_iteration: Explicit review pass number for this loop
        - reviewer_name: Reviewer agent name (e.g., code-quality-reviewer)
        - feedback_markdown: Full reviewer section markdown
        - score: Reviewer-local score (0..100)
        - blockers: Reviewer blocker list
        - findings: List of finding objects with `priority` and `feedback`

        Returns:
        - MCPResponse: Contains loop id and storage confirmation
        """
        await ctx.info(
            f'Storing reviewer result for loop {loop_id} (iteration={review_iteration}, reviewer={reviewer_name})'
        )
        try:
            result = await _get_tools(ctx).store_reviewer_result(
                loop_id=loop_id,
                review_iteration=review_iteration,
                reviewer_name=reviewer_name,
                feedback_markdown=feedback_markdown,
                score=score,
                blockers=blockers,
                findings=findings,
            )
            await ctx.info(f'Stored reviewer result for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to store reviewer result: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ToolError(f'Unexpected error storing reviewer result: {str(e)}')

    @mcp.tool()
    async def consolidate_review_cycle(
        loop_id: str, review_iteration: int, active_reviewers: list[str], ctx: Context
    ) -> MCPResponse:
        """Consolidate stored reviewer results into one CriticFeedback for this iteration.

        Parameters:
        - loop_id: Loop identifier
        - review_iteration: Explicit review pass number for this loop
        - active_reviewers: Reviewer names invoked for this pass

        Returns:
        - MCPResponse: Consolidation confirmation with score/iteration metadata
        """
        await ctx.info(f'Consolidating review cycle for loop {loop_id} iteration {review_iteration}')
        try:
            result = await _get_tools(ctx).consolidate_review_cycle(loop_id, review_iteration, active_reviewers)
            await ctx.info(f'Consolidated review cycle for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to consolidate review cycle: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ToolError(f'Unexpected error consolidating review cycle: {str(e)}')

    @mcp.tool()
    async def store_critic_feedback(loop_id: str, feedback_markdown: str, ctx: Context) -> MCPResponse:
        """Store critic feedback from automated assessment agents.

        Parses structured markdown into CriticFeedback model and stores in LoopState.
        Used by all critic agents (task-critic, plan-critic, analyst-critic, etc.).

        Parameters:
        - loop_id: Loop identifier
        - feedback_markdown: CriticFeedback in structured markdown format

        Returns:
        - MCPResponse: Contains loop_id, status, confirmation with score
        """
        await ctx.info(f'Storing critic feedback for loop {loop_id}')
        try:
            result = await _get_tools(ctx).store_critic_feedback(loop_id, feedback_markdown)
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
            result = await _get_tools(ctx).store_user_feedback(loop_id, feedback_markdown)
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
        Default retrieves 2 most recent iterations for stagnation detection context.

        Parameters:
        - loop_id: Loop identifier
        - count: Number of recent critic feedback iterations to retrieve (default: 2)
                 Agents can request more if needed for broader context

        Returns:
        - MCPResponse: Contains recent feedback in chronological markdown format
        """
        await ctx.info(f'Retrieving {count} recent feedback(s) for loop {loop_id}')
        try:
            result = await _get_tools(ctx).get_feedback(loop_id, count)
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
        """Store current analysis for the analyst validation loop.

        Stores business objectives analysis from plan-analyst for review by analyst-critic.

        Parameters:
        - loop_id (str): Analyst loop ID to store analysis for
        - analysis (str): Analysis markdown content

        Returns: MCPResponse with confirmation
        """
        await ctx.info(f'Storing analysis for loop {loop_id}')
        try:
            result = await _get_tools(ctx).store_current_analysis(loop_id, analysis)
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
        """Retrieve previous analysis from the analyst validation loop.

        Gets the most recent business objectives analysis stored by plan-analyst
        for quality validation by analyst-critic.

        Parameters:
        - loop_id (str): Analyst loop ID to retrieve analysis from

        Returns: MCPResponse containing the analysis markdown
        """
        await ctx.info(f'Retrieving previous analysis for loop {loop_id}')
        try:
            result = await _get_tools(ctx).get_previous_analysis(loop_id)
            await ctx.info(f'Retrieved analysis for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to retrieve analysis: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ResourceError(f'Analysis unavailable for loop {loop_id}: {str(e)}')
