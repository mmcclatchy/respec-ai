import logging
import re

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from src.models.enums import CriticAgent, Priority
from src.models.feedback import REVIEWER_EXECUTION_REPORT_MARKER, CriticFeedback, ReviewFinding, ReviewerResult
from src.models.phase import Phase
from src.utils.errors import LoopNotFoundError, PhaseNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.review_weighting import compute_frontend_ratio, compute_phase1_weights
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
        self._reviewer_max_scores: dict[CriticAgent, int] = {
            CriticAgent.AUTOMATED_QUALITY_CHECKER: 50,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER: 50,
            CriticAgent.DESIGN_CONFORMANCE_REVIEWER: 50,
            CriticAgent.CODE_QUALITY_REVIEWER: 25,
            CriticAgent.FRONTEND_REVIEWER: 25,
            CriticAgent.BACKEND_API_REVIEWER: 25,
            CriticAgent.DATABASE_REVIEWER: 25,
            CriticAgent.INFRASTRUCTURE_REVIEWER: 25,
            CriticAgent.CODING_STANDARDS_REVIEWER: 25,
        }
        self._phase1_core_weights: dict[CriticAgent, float] = {
            CriticAgent.AUTOMATED_QUALITY_CHECKER: 25.0,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER: 30.0,
            CriticAgent.CODE_QUALITY_REVIEWER: 20.0,
            CriticAgent.DESIGN_CONFORMANCE_REVIEWER: 20.0,
        }
        self._phase1_review_universe: list[CriticAgent] = [
            CriticAgent.AUTOMATED_QUALITY_CHECKER,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER,
            CriticAgent.CODE_QUALITY_REVIEWER,
            CriticAgent.DESIGN_CONFORMANCE_REVIEWER,
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
            for critic_feedback in critic_feedback_list:
                logger.debug(
                    'get_feedback: formatting stored iteration '
                    f'{critic_feedback.iteration} with score={critic_feedback.overall_score}, '
                    f'iteration={critic_feedback.iteration}'
                )
                feedback_parts.append(
                    f'## Iteration {critic_feedback.iteration} - Score: {critic_feedback.overall_score}\n'
                )
                feedback_parts.append(f'{critic_feedback.assessment_summary}\n')
                if critic_feedback.blockers:
                    feedback_parts.append('### Blockers')
                    for blocker in critic_feedback.blockers:
                        feedback_parts.append(f'- {blocker}')
                    feedback_parts.append('')
                if critic_feedback.key_issues:
                    feedback_parts.append('### Key Issues')
                    for issue in critic_feedback.key_issues:
                        feedback_parts.append(f'- {issue}')
                    feedback_parts.append('')
                if critic_feedback.recommendations:
                    feedback_parts.append('### Recommendations')
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
        max_score: int,
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

        parsed_reviewer_name = self._parse_reviewer_name(reviewer_name)
        expected_max_score = self._reviewer_max_scores.get(parsed_reviewer_name)
        if expected_max_score is not None and max_score != expected_max_score:
            raise ToolError(
                f'max_score for {parsed_reviewer_name.value} must be {expected_max_score}; received {max_score}'
            )
        validated_blockers = self._validate_reviewer_blockers(blockers or [])

        review_findings = [
            ReviewFinding(
                priority=Priority(item['priority']),
                feedback=self._validate_reviewer_finding_feedback(item['feedback']),
            )
            for item in findings
        ]
        reviewer_result = ReviewerResult(
            loop_id=loop_id,
            review_iteration=review_iteration,
            reviewer_name=parsed_reviewer_name,
            feedback_markdown=feedback_markdown,
            score=score,
            max_score=max_score,
            blockers=validated_blockers,
            findings=review_findings,
        )
        await self.state.upsert_reviewer_result(reviewer_result)
        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message=(
                f'Stored reviewer result for {reviewer_result.reviewer_name.value} '
                f'(iteration={review_iteration}, score={reviewer_result.score}/{reviewer_result.max_score})'
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
        stored_results = await self.state.list_latest_reviewer_results(
            loop_id,
            review_iteration,
            [name.value for name in active_critic_agents],
        )
        results_by_reviewer = {result.reviewer_name: result for result in stored_results}

        missing_reviewers = [name for name in active_critic_agents if name not in results_by_reviewer]
        if missing_reviewers:
            missing = ', '.join(name.value for name in missing_reviewers)
            raise ToolError(f'Cannot consolidate review cycle: missing reviewer submissions: {missing}')

        is_phase2 = active_critic_agents == [CriticAgent.CODING_STANDARDS_REVIEWER]
        universe = self._phase2_review_universe if is_phase2 else self._phase1_review_universe

        active_results = [results_by_reviewer[name] for name in active_critic_agents]
        if is_phase2:
            weights_by_reviewer = self._phase2_weights_for_results(active_results)
        else:
            frontend_ratio = compute_frontend_ratio(await self._get_phase_for_loop(loop_id))
            weights_by_reviewer = self._phase1_weights_for_results(active_results, frontend_ratio)
        overall_score, weighted_contributions = self._compute_weighted_score(active_results, weights_by_reviewer)

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
        reused_count = sum(1 for result in active_results if result.review_iteration < review_iteration)
        summary = (
            f'Consolidated {len(active_results)} reviewer result(s) for iteration {review_iteration}. '
            f'Composite score={overall_score}/100. '
            + ('[BLOCKING] Active blockers detected.' if blocker_active else 'No active blockers detected.')
        )
        if reused_count:
            summary += f' Reused reviewer results from prior iterations: {reused_count}.'
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
                reviewer_weight = weights_by_reviewer.get(reviewer, 0.0)
                result_source = (
                    'current iteration'
                    if result.review_iteration == review_iteration
                    else f'reused from iteration {result.review_iteration}'
                )
                detail_lines.append(f'- Result Source: {result_source}')
                detail_lines.append(f'- Score: {result.score}/{result.max_score}')
                detail_lines.append(f'- Normalized Score: {result.normalized_score}/100')
                detail_lines.append(f'- Configured Weight: {reviewer_weight:g}')
                detail_lines.append(f'- Weighted Contribution: {weighted_contributions.get(reviewer, 0.0):.2f}/100')
                detail_lines.append(
                    '- Full Reviewer Feedback: retrieve with '
                    f'get_reviewer_result(loop_id="{loop_id}", '
                    f'review_iteration={result.review_iteration}, reviewer_name="{reviewer.value}")'
                )
                if result.blockers:
                    detail_lines.append('- Blockers:')
                    detail_lines.extend([f'  - {blocker}' for blocker in result.blockers])
                else:
                    detail_lines.append('- Blockers: none')
                if result.findings:
                    detail_lines.append('- Findings:')
                    detail_lines.extend(
                        [f'  - [Severity:{finding.priority.value}] {finding.feedback}' for finding in result.findings]
                    )
                else:
                    detail_lines.append('- Findings: none')
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
            blockers=all_blockers,
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

    async def get_reviewer_result(
        self,
        loop_id: str,
        review_iteration: int,
        reviewer_name: str,
    ) -> MCPResponse:
        if not loop_id or not loop_id.strip():
            raise ToolError('Loop ID cannot be empty')
        if review_iteration < 1:
            raise ToolError('review_iteration must be >= 1')
        if not reviewer_name or not reviewer_name.strip():
            raise ToolError('reviewer_name cannot be empty')

        try:
            loop_state = await self.state.get_loop(loop_id)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

        parsed_reviewer_name = self._parse_reviewer_name(reviewer_name)
        try:
            reviewer_result = await self.state.get_reviewer_result(
                loop_id,
                review_iteration,
                parsed_reviewer_name.value,
            )
        except ValueError as e:
            raise ResourceError(str(e)) from e

        message = (
            '# Reviewer Result\n\n'
            f'- Loop ID: {loop_id}\n'
            f'- Review Iteration: {review_iteration}\n'
            f'- Reviewer: {reviewer_result.reviewer_name.value}\n'
            f'- Score: {reviewer_result.score}/{reviewer_result.max_score}\n'
            f'- Normalized Score: {reviewer_result.normalized_score}/100\n'
            f'- Blockers: {len(reviewer_result.blockers)}\n'
            f'- Findings: {len(reviewer_result.findings)}\n\n'
            '## Full Feedback Markdown\n\n'
            f'{reviewer_result.feedback_markdown}'
        )

        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message=message,
        )

    async def get_reviewer_feedback_context(
        self,
        loop_id: str,
        review_iteration: int,
        active_reviewers: list[str],
    ) -> MCPResponse:
        """Get curated reviewer context for active reviewers at or before an iteration."""
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
        stored_results = await self.state.list_latest_reviewer_results(
            loop_id,
            review_iteration,
            [name.value for name in active_critic_agents],
        )
        results_by_reviewer = {result.reviewer_name: result for result in stored_results}
        missing_reviewers = [name for name in active_critic_agents if name not in results_by_reviewer]
        if missing_reviewers:
            missing = ', '.join(name.value for name in missing_reviewers)
            raise ToolError(f'Cannot retrieve reviewer feedback context: missing reviewer submissions: {missing}')

        context_lines = [
            '# Curated Reviewer Feedback Context',
            '',
            f'- Loop ID: {loop_id}',
            f'- Review Iteration: {review_iteration}',
            '- Scope: active reviewers only',
            '- Excludes: non-actionable execution reports, rubric weights, and consolidation bookkeeping',
            '',
        ]

        for reviewer in active_critic_agents:
            result = results_by_reviewer[reviewer]
            context_lines.append(f'## {reviewer.value}')

            result_source = (
                'current iteration'
                if result.review_iteration == review_iteration
                else f'reused from iteration {result.review_iteration}'
            )
            context_lines.append(f'- Result Source: {result_source}')
            context_lines.append(f'- Score: {result.score}/{result.max_score}')
            context_lines.append('- Blockers:')
            if result.blockers:
                context_lines.extend([f'  - {blocker}' for blocker in result.blockers])
            else:
                context_lines.append('  - none')
            context_lines.append('- Findings:')
            if result.findings:
                context_lines.extend(
                    [f'  - [Severity:{finding.priority.value}] {finding.feedback}' for finding in result.findings]
                )
            else:
                context_lines.append('  - none')
            context_lines.append('')
            actionable_excerpt = self._extract_actionable_reviewer_excerpt(result.feedback_markdown)
            context_lines.append('### Actionable Review Excerpts')
            context_lines.append(
                actionable_excerpt or 'No actionable markdown excerpts found; use structured findings.'
            )
            context_lines.append('')

        return MCPResponse(
            id=loop_id,
            status=loop_state.status,
            message='\n'.join(context_lines).strip(),
        )

    def _extract_actionable_reviewer_excerpt(self, feedback_markdown: str) -> str:
        sanitized = self._strip_reviewer_execution_report(feedback_markdown)
        actionable_sections = {
            'assessment results',
            'key issues',
            'recommendations',
            'findings',
            'required corrections',
            'seam review',
        }
        sections: list[str] = []
        lines = sanitized.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            heading_match = re.match(r'^(#{1,6})\s+(.+?)\s*$', line)
            if not heading_match:
                index += 1
                continue
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip().lower()
            if heading_text not in actionable_sections:
                index += 1
                continue

            section_lines = [line]
            index += 1
            while index < len(lines):
                next_match = re.match(r'^(#{1,6})\s+(.+?)\s*$', lines[index])
                if next_match and len(next_match.group(1)) <= heading_level:
                    break
                section_lines.append(lines[index])
                index += 1
            sections.append('\n'.join(section_lines).strip())

        return '\n\n'.join(section for section in sections if section).strip()

    def _strip_reviewer_execution_report(self, feedback_markdown: str) -> str:
        lines = feedback_markdown.splitlines()
        kept_lines: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if REVIEWER_EXECUTION_REPORT_MARKER not in line:
                kept_lines.append(line)
                index += 1
                continue

            heading_match = re.match(r'^(#{1,6})\s+', line)
            heading_level = len(heading_match.group(1)) if heading_match else 6
            index += 1
            while index < len(lines):
                next_match = re.match(r'^(#{1,6})\s+', lines[index])
                if next_match and len(next_match.group(1)) <= heading_level:
                    break
                index += 1

        return '\n'.join(kept_lines).strip()

    def _parse_and_validate_feedback(self, feedback_markdown: str) -> CriticFeedback:
        try:
            feedback = CriticFeedback.parse_markdown(feedback_markdown)
        except Exception as e:
            raise ToolError(f'Failed to parse feedback markdown: {str(e)}')

        # Validation checks - look for obvious template placeholders.
        if 'Critic Feedback: UNKNOWN' in feedback_markdown or '# Critic Feedback: UNKNOWN' in feedback_markdown:
            raise ToolError('Feedback must specify a valid critic agent')
        if '# Critic Feedback:' not in feedback_markdown:
            raise ToolError('Feedback missing critic feedback header')

        return feedback

    async def _get_phase_for_loop(self, loop_id: str) -> Phase | None:
        # Design-derived, not iteration-derived (README cross-cutting risk #2, B4): the Phase
        # document only changes via an explicit amendment, never via which files a given
        # iteration happened to touch, so weights computed from it stay stable for the whole
        # loop. A loop with no linked Phase (e.g. a phase-2/patch loop, or a test that never
        # links one) degrades to frontend_ratio=0.0 -- the pre-phase-6 fixed weights.
        try:
            return await self.state.get_phase_by_loop(loop_id)
        except (LoopNotFoundError, PhaseNotFoundError):
            return None

    def _phase1_weights_for_results(
        self, active_results: list[ReviewerResult], frontend_ratio: float
    ) -> dict[CriticAgent, float]:
        active_reviewers = {result.reviewer_name for result in active_results}
        weights = compute_phase1_weights(self._phase1_core_weights, active_reviewers, frontend_ratio)

        unweighted_reviewers = active_reviewers - set(weights)
        if unweighted_reviewers:
            reviewers = ', '.join(sorted(reviewer.value for reviewer in unweighted_reviewers))
            raise ToolError(f'Cannot compute Phase 1 score: no configured weight for reviewer(s): {reviewers}')
        return weights

    def _phase2_weights_for_results(self, active_results: list[ReviewerResult]) -> dict[CriticAgent, float]:
        active_reviewers = {result.reviewer_name for result in active_results}
        weights = {CriticAgent.CODING_STANDARDS_REVIEWER: 100.0}
        unweighted_reviewers = active_reviewers - set(weights)
        if unweighted_reviewers:
            reviewers = ', '.join(sorted(reviewer.value for reviewer in unweighted_reviewers))
            raise ToolError(f'Cannot compute Phase 2 score: no configured weight for reviewer(s): {reviewers}')
        return {reviewer: weight for reviewer, weight in weights.items() if reviewer in active_reviewers}

    def _compute_weighted_score(
        self,
        active_results: list[ReviewerResult],
        weights_by_reviewer: dict[CriticAgent, float],
    ) -> tuple[int, dict[CriticAgent, float]]:
        if not active_results:
            return 0, {}

        active_weight_total = sum(weights_by_reviewer.get(result.reviewer_name, 0.0) for result in active_results)
        if active_weight_total <= 0:
            raise ToolError('Cannot compute review score: active reviewer weight total is zero')

        weighted_contributions: dict[CriticAgent, float] = {}
        for result in active_results:
            reviewer_weight = weights_by_reviewer[result.reviewer_name]
            weighted_contributions[result.reviewer_name] = (
                (result.score / result.max_score) * reviewer_weight / active_weight_total * 100
            )

        raw_score = sum(weighted_contributions.values())
        all_reviewers_perfect = all(result.score == result.max_score for result in active_results)
        score = int(round(raw_score))
        if all_reviewers_perfect:
            score = 100
        else:
            score = min(99, score)
        return max(0, min(100, score)), weighted_contributions

    def _validate_reviewer_blockers(self, blockers: list[str]) -> list[str]:
        invalid_blockers = CriticFeedback.invalid_blocker_values(blockers)
        if invalid_blockers:
            invalid_values = ', '.join(repr(blocker) for blocker in invalid_blockers)
            raise ToolError(
                'Reviewer blockers must be actionable non-empty strings; use [] when no blockers exist. '
                f'Remove invalid blocker entries: {invalid_values}'
            )
        contaminated_blockers = [blocker for blocker in blockers if REVIEWER_EXECUTION_REPORT_MARKER in blocker]
        if contaminated_blockers:
            invalid_values = ', '.join(repr(blocker) for blocker in contaminated_blockers)
            raise ToolError(
                'Reviewer blockers must contain actionable implementation issues only. '
                f'Remove non-actionable execution-report content from blockers: {invalid_values}'
            )
        return blockers

    def _validate_reviewer_finding_feedback(self, feedback: str) -> str:
        if REVIEWER_EXECUTION_REPORT_MARKER in feedback:
            raise ToolError(
                'Reviewer findings must contain actionable implementation issues only. '
                'Remove non-actionable execution-report content from findings.'
            )
        return feedback

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
        max_score: int,
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
        - score: Reviewer-local earned score
        - max_score: Reviewer-local maximum score
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
                max_score=max_score,
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
    async def get_reviewer_result(
        loop_id: str,
        review_iteration: int,
        reviewer_name: str,
        ctx: Context,
    ) -> MCPResponse:
        """Retrieve one stored reviewer result including its full markdown payload.

        Parameters:
        - loop_id: Loop identifier
        - review_iteration: Explicit review pass number for this loop
        - reviewer_name: Reviewer agent name (e.g., code-quality-reviewer)

        Returns:
        - MCPResponse: Reviewer metadata plus full feedback markdown
        """
        await ctx.info(
            f'Retrieving reviewer result for loop {loop_id} (iteration={review_iteration}, reviewer={reviewer_name})'
        )
        try:
            result = await _get_tools(ctx).get_reviewer_result(
                loop_id=loop_id,
                review_iteration=review_iteration,
                reviewer_name=reviewer_name,
            )
            await ctx.info(f'Retrieved reviewer result for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to retrieve reviewer result: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ResourceError(f'Reviewer result unavailable for loop {loop_id}: {str(e)}')

    @mcp.tool()
    async def consolidate_review_cycle(
        loop_id: str, review_iteration: int, active_reviewers: list[str], ctx: Context
    ) -> MCPResponse:
        """Consolidate stored reviewer results into one CriticFeedback for this iteration.

        Parameters:
        - loop_id: Loop identifier
        - review_iteration: Explicit review pass number for this loop
        - active_reviewers: Full reviewer roster to consolidate for this pass. Each reviewer uses the latest stored
          result at or before review_iteration.

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
        Used by all critic agents (phase-critic, plan-critic, analyst-critic, etc.).

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
    async def get_reviewer_feedback_context(
        loop_id: str,
        review_iteration: int,
        active_reviewers: list[str],
        ctx: Context,
    ) -> MCPResponse:
        """Get curated reviewer feedback context for the active reviewers in one iteration.

        Parameters:
        - loop_id: Loop identifier
        - review_iteration: Review iteration to retrieve context for
        - active_reviewers: Reviewer names to include; only these reviewers are returned

        Returns:
        - MCPResponse: Curated markdown with score, source, blockers, findings, and actionable excerpts
        """
        await ctx.info(f'Retrieving reviewer feedback context for loop {loop_id} iteration {review_iteration}')
        try:
            result = await _get_tools(ctx).get_reviewer_feedback_context(
                loop_id=loop_id,
                review_iteration=review_iteration,
                active_reviewers=active_reviewers,
            )
            await ctx.info(f'Retrieved reviewer feedback context for loop {loop_id}')
            return result
        except (ToolError, ResourceError) as e:
            await ctx.error(f'Failed to retrieve reviewer feedback context: {str(e)}')
            raise
        except Exception as e:
            await ctx.error(f'Unexpected error: {str(e)}')
            raise ResourceError(f'Reviewer feedback context unavailable for loop {loop_id}: {str(e)}')

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
