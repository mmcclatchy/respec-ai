import pytest
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.feedback_tools_unified import UnifiedFeedbackTools
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def plan_name() -> str:
    return 'test-plan'


class TestUnifiedFeedbackToolsMemoryBoundaries:
    @pytest.mark.asyncio
    async def test_user_feedback_persists_via_state_manager_across_tool_instances(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(loop, plan_name)

        writer = UnifiedFeedbackTools(state)
        await writer.store_user_feedback(loop.id, 'user feedback 1')
        await writer.store_user_feedback(loop.id, 'user feedback 2')
        await writer.store_user_feedback(loop.id, 'user feedback 3')

        # New tool instance must read from manager-backed storage, not local caches.
        reader = UnifiedFeedbackTools(state)
        response = await reader.get_feedback(loop.id, count=1)

        assert 'No feedback available' not in response.message
        assert '## User Input 1' in response.message
        assert 'user feedback 1' in response.message
        assert '## User Input 3' in response.message
        assert 'user feedback 3' in response.message

    @pytest.mark.asyncio
    async def test_get_feedback_count_applies_only_to_critic_feedback(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(loop, plan_name)

        feedback1 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.PLAN_CRITIC,
            iteration=1,
            overall_score=70,
            assessment_summary='Assessment 1',
            detailed_feedback='Details 1',
            key_issues=[],
            recommendations=[],
        )
        feedback2 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.PLAN_CRITIC,
            iteration=2,
            overall_score=75,
            assessment_summary='Assessment 2',
            detailed_feedback='Details 2',
            blockers=['Missing required section: Risk Management'],
            key_issues=[],
            recommendations=[],
        )
        loop.add_feedback(feedback1)
        loop.add_feedback(feedback2)
        await state.save_loop(loop)

        tools = UnifiedFeedbackTools(state)
        await tools.store_user_feedback(loop.id, 'user feedback 1')
        await tools.store_user_feedback(loop.id, 'user feedback 2')

        response = await tools.get_feedback(loop.id, count=1)

        assert 'Assessment 2' in response.message
        assert 'Assessment 1' not in response.message
        assert '### Blockers' in response.message
        assert 'Missing required section: Risk Management' in response.message
        assert 'user feedback 1' in response.message
        assert 'user feedback 2' in response.message

    @pytest.mark.asyncio
    async def test_get_feedback_preserves_stored_iteration_numbers(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(loop, plan_name)

        loop.add_feedback(
            CriticFeedback(
                loop_id=loop.id,
                critic_agent=CriticAgent.PLAN_CRITIC,
                iteration=2,
                overall_score=82,
                assessment_summary='Assessment 2',
                detailed_feedback='Details 2',
                key_issues=[],
                recommendations=[],
            )
        )
        loop.add_feedback(
            CriticFeedback(
                loop_id=loop.id,
                critic_agent=CriticAgent.PLAN_CRITIC,
                iteration=4,
                overall_score=91,
                assessment_summary='Assessment 4',
                detailed_feedback='Details 4',
                key_issues=[],
                recommendations=[],
            )
        )
        await state.save_loop(loop)

        tools = UnifiedFeedbackTools(state)
        response = await tools.get_feedback(loop.id, count=2)

        assert '## Iteration 2 - Score: 82' in response.message
        assert '## Iteration 4 - Score: 91' in response.message
        assert '## Iteration 1 - Score: 82' not in response.message

    @pytest.mark.asyncio
    async def test_analysis_upsert_and_retrieve_via_state_manager(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.ANALYST)
        await state.add_loop(loop, plan_name)

        tools = UnifiedFeedbackTools(state)
        await tools.store_current_analysis(loop.id, 'analysis v1')
        await tools.store_current_analysis(loop.id, 'analysis v2')

        result = await tools.get_previous_analysis(loop.id)
        assert 'analysis v2' in result.message
        assert 'analysis v1' not in result.message

    @pytest.mark.asyncio
    async def test_analyst_loop_critic_feedback_updates_loop_state_and_feedback_history(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.ANALYST)
        await state.add_loop(loop, plan_name)

        tools = UnifiedFeedbackTools(state)
        await tools.store_current_analysis(loop.id, 'analysis artifact v1')

        feedback_markdown = """# Critic Feedback: ANALYST-CRITIC

## Assessment Summary
- **Loop ID**: analyst-loop
- **Iteration**: 1
- **Overall Score**: 84
- **Assessment Summary**: Extraction quality is solid, but one structural issue remains.

## Analysis

### Semantic Accuracy Assessment

Analysis maps well to the source plan.

### Completeness Evaluation

One required subsection is still missing.

### Quantification Quality

Metrics are mostly grounded in the source plan.

### Evidence and Findings

Findings trace back to the strategic plan.

## Issues and Recommendations

### Blockers

- Missing Required Analysis Section - BLOCKING: Stakeholder Analysis subsection is absent

### Key Issues

- Stakeholder mapping is thinner than the source plan.

### Recommendations

- Add the missing stakeholder analysis subsection and expand role coverage.
"""

        response = await tools.store_critic_feedback(loop.id, feedback_markdown)
        assert 'Stored critic feedback for loop' in response.message

        feedback_response = await tools.get_feedback(loop.id, count=1)
        assert '## Iteration 1 - Score: 84' in feedback_response.message
        assert '### Blockers' in feedback_response.message
        assert 'Stakeholder Analysis subsection is absent' in feedback_response.message

        analysis_response = await tools.get_previous_analysis(loop.id)
        assert 'analysis artifact v1' in analysis_response.message

        stored_loop = await state.get_loop(loop.id)
        assert stored_loop.current_score == 84
        assert len(stored_loop.feedback_history) == 1
        assert stored_loop.feedback_history[0].critic_agent == CriticAgent.ANALYST_CRITIC
        assert stored_loop.feedback_history[0].blockers == [
            'Missing Required Analysis Section - BLOCKING: Stakeholder Analysis subsection is absent'
        ]

    @pytest.mark.asyncio
    async def test_stale_loop_lookup_returns_resource_error(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=1)
        tools = UnifiedFeedbackTools(state)

        stale_loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(stale_loop, plan_name)
        await tools.store_user_feedback(stale_loop.id, 'stale feedback')
        await tools.store_current_analysis(stale_loop.id, 'stale analysis')

        # Adding a second loop evicts stale_loop from active state manager history.
        await state.add_loop(LoopState(loop_type=LoopType.PHASE), plan_name)

        with pytest.raises(ResourceError, match='Loop does not exist'):
            await tools.get_feedback(stale_loop.id, count=1)

    @pytest.mark.asyncio
    async def test_store_critic_feedback_fails_fast_on_missing_required_markdown_fields(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.PHASE)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        invalid_feedback_markdown = """# Critic Feedback: PHASE-CRITIC

## Assessment Summary
- **Loop ID**: test-loop
- **Iteration**: 1
- **Assessment Summary**: Missing score should fail fast

## Analysis

Detailed feedback present.

## Issues and Recommendations

### Key Issues

- Example issue

### Recommendations

- Example recommendation
"""

        with pytest.raises(ToolError, match='Missing required assessment fields: overall_score'):
            await tools.store_critic_feedback(loop.id, invalid_feedback_markdown)

    @pytest.mark.asyncio
    async def test_store_critic_feedback_rejects_placeholder_blockers_without_persisting(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        invalid_feedback_markdown = """# Critic Feedback: TASK-CRITIC

## Assessment Summary
- **Loop ID**: task-loop
- **Iteration**: 1
- **Overall Score**: 100
- **Assessment Summary**: Task is ready and has no blockers.

## Analysis

The task is implementation-ready.

## Issues and Recommendations

### Key Issues

- None identified

### Blockers

- None.

### Recommendations

- None provided
"""

        with pytest.raises(ToolError, match='Blockers must be actionable non-empty strings'):
            await tools.store_critic_feedback(loop.id, invalid_feedback_markdown)

        stored_loop = await state.get_loop(loop.id)
        assert stored_loop.current_score == 0
        assert stored_loop.feedback_history == []


class TestDeterministicReviewConsolidation:
    @pytest.mark.asyncio
    async def test_store_reviewer_result_and_consolidate_phase1(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='automated-quality-checker',
            feedback_markdown='### Automated Quality Check (Score: 45/50)',
            score=45,
            max_score=50,
            blockers=[],
            findings=[{'priority': 'P2', 'feedback': 'Minor lint issue in src/main.py:10'}],
        )
        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='spec-alignment-reviewer',
            feedback_markdown='### Spec Alignment (Score: 47/50)',
            score=47,
            max_score=50,
            blockers=[],
            findings=[{'priority': 'P1', 'feedback': 'Acceptance criterion AC-3 partially implemented'}],
        )
        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='code-quality-reviewer',
            feedback_markdown='### Code Quality (Score: 22/25)',
            score=22,
            max_score=25,
            blockers=[],
            findings=[],
        )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=1,
            active_reviewers=[
                'automated-quality-checker',
                'spec-alignment-reviewer',
                'code-quality-reviewer',
            ],
        )

        assert consolidate_response.current_score == 91
        feedback = await tools.get_feedback(loop.id, count=1)
        assert 'Consolidated 3 reviewer result(s) for iteration 1.' in feedback.message
        assert '[Severity:P1]' in feedback.message
        assert '[Severity:P2]' in feedback.message
        stored_loop = await state.get_loop(loop.id)
        detailed_feedback = stored_loop.feedback_history[-1].detailed_feedback
        assert '- Score: 45/50' in detailed_feedback
        assert '- Normalized Score: 90/100' in detailed_feedback
        assert '- Weighted Contribution:' in detailed_feedback

    @pytest.mark.asyncio
    async def test_consolidate_reuses_latest_prior_reviewer_result(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='code-quality-reviewer',
            feedback_markdown='### Code Quality (Score: 25/25)',
            score=25,
            max_score=25,
            blockers=[],
            findings=[{'priority': 'P3', 'feedback': 'Prior advisory in src/main.py:10'}],
        )
        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=2,
            reviewer_name='automated-quality-checker',
            feedback_markdown='### Automated Quality Check (Score: 50/50)',
            score=50,
            max_score=50,
            blockers=[],
            findings=[],
        )
        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=2,
            reviewer_name='spec-alignment-reviewer',
            feedback_markdown='### Spec Alignment (Score: 50/50)',
            score=50,
            max_score=50,
            blockers=[],
            findings=[],
        )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=2,
            active_reviewers=[
                'automated-quality-checker',
                'spec-alignment-reviewer',
                'code-quality-reviewer',
            ],
        )

        assert consolidate_response.current_score == 100
        stored_loop = await state.get_loop(loop.id)
        consolidated_feedback = stored_loop.feedback_history[-1]
        assert 'Reused reviewer results from prior iterations: 1.' in consolidated_feedback.assessment_summary
        assert '#### code-quality-reviewer' in consolidated_feedback.detailed_feedback
        assert '- Result Source: reused from iteration 1' in consolidated_feedback.detailed_feedback
        assert '- Result Source: current iteration' in consolidated_feedback.detailed_feedback
        assert '[Severity:P3] [code-quality-reviewer] Prior advisory in src/main.py:10' in (
            consolidated_feedback.key_issues
        )

    @pytest.mark.asyncio
    async def test_consolidate_uses_newest_prior_reviewer_result_and_ignores_future(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        for iteration, score in [(1, 20), (2, 24), (4, 10)]:
            await tools.store_reviewer_result(
                loop_id=loop.id,
                review_iteration=iteration,
                reviewer_name='code-quality-reviewer',
                feedback_markdown=f'### Code Quality (Score: {score}/25)',
                score=score,
                max_score=25,
                blockers=[],
                findings=[],
            )

        latest_results = await state.list_latest_reviewer_results(
            loop.id,
            3,
            ['code-quality-reviewer'],
        )

        assert len(latest_results) == 1
        assert latest_results[0].review_iteration == 2
        assert latest_results[0].score == 24

    @pytest.mark.asyncio
    async def test_consolidate_fails_when_only_future_reviewer_result_exists(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=3,
            reviewer_name='code-quality-reviewer',
            feedback_markdown='### Code Quality (Score: 25/25)',
            score=25,
            max_score=25,
            blockers=[],
            findings=[],
        )

        with pytest.raises(ToolError, match='missing reviewer submissions: code-quality-reviewer'):
            await tools.consolidate_review_cycle(
                loop_id=loop.id,
                review_iteration=2,
                active_reviewers=['code-quality-reviewer'],
            )

    @pytest.mark.asyncio
    async def test_reviewer_local_max_score_normalizes_to_composite_percentage(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='automated-quality-checker',
            feedback_markdown='### Automated Quality Check (Score: 50/50)',
            score=50,
            max_score=50,
            blockers=[],
            findings=[],
        )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=1,
            active_reviewers=['automated-quality-checker'],
        )

        assert consolidate_response.current_score == 100
        feedback = await tools.get_feedback(loop.id, count=1)
        assert 'Composite score=100/100.' in feedback.message
        stored_loop = await state.get_loop(loop.id)
        detailed_feedback = stored_loop.feedback_history[-1].detailed_feedback
        assert '- Score: 50/50' in detailed_feedback
        assert '- Normalized Score: 100/100' in detailed_feedback

    @pytest.mark.asyncio
    async def test_all_active_phase1_reviewers_perfect_returns_composite_100(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)
        reviewers = [
            ('automated-quality-checker', 50),
            ('spec-alignment-reviewer', 50),
            ('code-quality-reviewer', 25),
            ('frontend-reviewer', 25),
            ('backend-api-reviewer', 25),
            ('database-reviewer', 25),
            ('infrastructure-reviewer', 25),
        ]

        for reviewer_name, max_score in reviewers:
            await tools.store_reviewer_result(
                loop_id=loop.id,
                review_iteration=1,
                reviewer_name=reviewer_name,
                feedback_markdown=f'### {reviewer_name} (Score: {max_score}/{max_score})',
                score=max_score,
                max_score=max_score,
                blockers=[],
                findings=[],
            )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=1,
            active_reviewers=[reviewer_name for reviewer_name, _ in reviewers],
        )

        assert consolidate_response.current_score == 100
        stored_loop = await state.get_loop(loop.id)
        detailed_feedback = stored_loop.feedback_history[-1].detailed_feedback
        assert '- Weighted Contribution:' in detailed_feedback

    @pytest.mark.asyncio
    async def test_non_perfect_phase1_reviewers_cannot_round_up_to_composite_100(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)
        reviewers = [
            ('automated-quality-checker', 50, 50),
            ('spec-alignment-reviewer', 50, 50),
            ('code-quality-reviewer', 25, 25),
            ('frontend-reviewer', 25, 24),
            ('backend-api-reviewer', 25, 25),
            ('database-reviewer', 25, 25),
            ('infrastructure-reviewer', 25, 25),
        ]

        for reviewer_name, max_score, score in reviewers:
            await tools.store_reviewer_result(
                loop_id=loop.id,
                review_iteration=1,
                reviewer_name=reviewer_name,
                feedback_markdown=f'### {reviewer_name} (Score: {score}/{max_score})',
                score=score,
                max_score=max_score,
                blockers=[],
                findings=[],
            )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=1,
            active_reviewers=[reviewer_name for reviewer_name, _, _ in reviewers],
        )

        assert consolidate_response.current_score == 99
        stored_loop = await state.get_loop(loop.id)
        detailed_feedback = stored_loop.feedback_history[-1].detailed_feedback
        assert '- Score: 24/25' in detailed_feedback
        assert '- Weighted Contribution: 3.60/100' in detailed_feedback

    @pytest.mark.asyncio
    async def test_store_reviewer_result_rejects_placeholder_blockers_without_persisting(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        with pytest.raises(ToolError, match='Reviewer blockers must be actionable non-empty strings'):
            await tools.store_reviewer_result(
                loop_id=loop.id,
                review_iteration=1,
                reviewer_name='automated-quality-checker',
                feedback_markdown='### Automated Quality Check (Score: 50/50)',
                score=50,
                max_score=50,
                blockers=['No blockers'],
                findings=[],
            )

        stored_results = await state.list_reviewer_results(loop.id, 1)
        assert stored_results == []

    @pytest.mark.asyncio
    async def test_store_reviewer_result_rejects_blank_blockers_without_persisting(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        with pytest.raises(ToolError, match='Reviewer blockers must be actionable non-empty strings'):
            await tools.store_reviewer_result(
                loop_id=loop.id,
                review_iteration=1,
                reviewer_name='automated-quality-checker',
                feedback_markdown='### Automated Quality Check (Score: 50/50)',
                score=50,
                max_score=50,
                blockers=[' '],
                findings=[],
            )

        stored_results = await state.list_reviewer_results(loop.id, 1)
        assert stored_results == []

    @pytest.mark.asyncio
    async def test_consolidate_persists_reviewer_blockers_structurally(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='automated-quality-checker',
            feedback_markdown='### Automated Quality Check (Score: 50/50)',
            score=50,
            max_score=50,
            blockers=['Required integration test is failing.'],
            findings=[],
        )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=1,
            active_reviewers=['automated-quality-checker'],
        )

        assert consolidate_response.current_score == 100
        stored_loop = await state.get_loop(loop.id)
        consolidated_feedback = stored_loop.feedback_history[-1]
        assert consolidated_feedback.blockers == ['[automated-quality-checker] Required integration test is failing.']
        assert '[BLOCKING] [automated-quality-checker] Required integration test is failing.' in (
            consolidated_feedback.key_issues
        )

    @pytest.mark.asyncio
    async def test_store_reviewer_result_rejects_wrong_max_score(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        with pytest.raises(ToolError, match='max_score for automated-quality-checker must be 50'):
            await tools.store_reviewer_result(
                loop_id=loop.id,
                review_iteration=1,
                reviewer_name='automated-quality-checker',
                feedback_markdown='### Automated Quality Check (Score: 100/100)',
                score=100,
                max_score=100,
                blockers=[],
                findings=[],
            )

    @pytest.mark.asyncio
    async def test_consolidate_requires_all_active_reviewers(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='coding-standards-reviewer',
            feedback_markdown='### Coding Standards Review (Score: 23/25)',
            score=23,
            max_score=25,
            blockers=[],
            findings=[],
        )

        with pytest.raises(ToolError, match='missing reviewer submissions'):
            await tools.consolidate_review_cycle(
                loop_id=loop.id,
                review_iteration=1,
                active_reviewers=['coding-standards-reviewer', 'code-quality-reviewer'],
            )
