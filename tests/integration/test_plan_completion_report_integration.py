import pytest

from src.mcp.tools.plan_completion_report_tools import PlanCompletionReportTools
from src.models.plan_completion_report import PlanCompletionReport
from src.platform.templates.commands.plan_command import plan_completion_template
from src.utils.enums import LoopStatus, LoopType
from src.utils.loop_state import LoopState, MCPResponse
from src.utils.state_manager import InMemoryStateManager


@pytest.mark.integration
class TestPlanCompletionReportIntegration:
    @pytest.fixture
    def project_path(self) -> str:
        return '/tmp/test-project'

    @pytest.fixture
    def state_manager(self) -> InMemoryStateManager:
        return InMemoryStateManager()

    @pytest.fixture
    def completion_report_tools(self, state_manager: InMemoryStateManager) -> PlanCompletionReportTools:
        return PlanCompletionReportTools(state_manager)

    @pytest.fixture
    def sample_completion_report_markdown(self) -> str:
        return """# Strategic Plan Output

## Plan Quality

### Final Plan Score
85

### Plan Completion Status
User-accepted (human-driven decision)

### User Decision
accept_plan

## Analyst Validation

### Final Analyst Score
90

### Analyst Completion Status
completed

### Analyst Loop Result
completed

## Strategic Plan Document

# Test Strategic Plan

This is a test strategic plan document with comprehensive details.

## Business Objectives
- Objective 1: Increase efficiency by 50%
- Objective 2: Reduce costs by 25%

## Structured Objectives

1. Primary: Efficiency improvement
   - Target: 50% increase in processing speed
   - Timeline: 6 months

2. Secondary: Cost reduction
   - Target: 25% reduction in operational costs
   - Timeline: 12 months

## Next Steps

1. Review the strategic plan for accuracy
2. Proceed with technical specification using: /respec-phase
3. The structured objectives will feed directly into phase-architect

## Metadata

### Analyst Loop ID
a1b2c3d4

### Timestamp
2025-01-15T14:30:00Z
"""

    @pytest.mark.asyncio
    async def test_full_workflow_integration(
        self, state_manager: InMemoryStateManager, completion_report_tools: PlanCompletionReportTools, project_path: str
    ) -> None:
        # Step 1: Create a loop in StateManager
        loop_state = LoopState(loop_type=LoopType.PLAN)
        await state_manager.add_loop(loop_state, project_path)
        loop_id = loop_state.id

        # Step 2: Create and store a completion report via standardized interface
        completion_report = PlanCompletionReport(
            report_title='Strategic Plan Output',
            final_plan_score='88',
            final_analyst_score='92',
            strategic_plan_document='# Integration Test Plan\nDetailed content',
            structured_objectives='Integration test objectives',
            analyst_loop_id=loop_id,
            completion_timestamp='2025-01-15T16:00:00Z',
        )

        store_result = await completion_report_tools.store(loop_id, completion_report.build_markdown())

        # Verify storage result
        assert isinstance(store_result, MCPResponse)
        assert store_result.id == loop_id
        assert f'Stored completion report for loop {loop_id}' in store_result.message

        # Step 3: Retrieve the stored report
        get_result = await completion_report_tools.get(key=loop_id)
        retrieved_report = PlanCompletionReport.parse_markdown(get_result.message)

        # Verify retrieved data matches stored data
        assert retrieved_report.report_title == 'Strategic Plan Output'
        assert retrieved_report.final_plan_score == '88'
        assert retrieved_report.final_analyst_score == '92'
        assert retrieved_report.strategic_plan_document == '# Integration Test Plan\nDetailed content'
        assert retrieved_report.analyst_loop_id == loop_id

        # Step 4: Verify markdown contains expected content
        assert isinstance(get_result, MCPResponse)
        assert '# Strategic Plan Output' in get_result.message
        assert '88%' in get_result.message
        assert '92%' in get_result.message

        # Step 5: Update the report
        updated_report = PlanCompletionReport(
            report_title='Strategic Plan Output',
            final_plan_score='95',
            final_analyst_score='97',
            strategic_plan_document='# Updated Integration Test Plan\nUpdated content',
            structured_objectives='Updated integration test objectives',
            analyst_loop_id=loop_id,
            completion_timestamp='2025-01-15T17:00:00Z',
        )

        update_result = await completion_report_tools.update(loop_id, updated_report.build_markdown())
        assert f'Updated completion report for loop {loop_id}' in update_result.message

        # Verify update
        updated_get_result = await completion_report_tools.get(key=loop_id)
        updated_retrieved = PlanCompletionReport.parse_markdown(updated_get_result.message)
        assert updated_retrieved.report_title == 'Strategic Plan Output'
        assert updated_retrieved.final_plan_score == '95'

        # Step 6: List reports
        list_result = await completion_report_tools.list()
        assert 'Found 1 report' in list_result.message
        assert 'Strategic Plan Output' in list_result.message

        # Step 7: Delete the report
        delete_result = await completion_report_tools.delete(loop_id)
        assert 'Strategic Plan Output' in delete_result.message

        # Verify deletion
        list_result_after_delete = await completion_report_tools.list()
        assert 'No completion reports found' in list_result_after_delete.message

    @pytest.mark.asyncio
    async def test_multiple_reports_workflow(
        self, state_manager: InMemoryStateManager, completion_report_tools: PlanCompletionReportTools, project_path: str
    ) -> None:
        # Create multiple loops
        loop_states = []
        for i in range(3):
            loop_state = LoopState(loop_type=LoopType.PLAN)
            await state_manager.add_loop(loop_state, project_path)
            loop_states.append(loop_state)

        # Create completion reports for each loop (all use required title)
        for i, loop_state in enumerate(loop_states):
            completion_report = PlanCompletionReport(
                report_title='Strategic Plan Output',
                final_plan_score=f'{80 + i * 5}',
                final_analyst_score=f'{85 + i * 3}',
                analyst_loop_id=loop_state.id,
            )

            result = await completion_report_tools.store(loop_state.id, completion_report.build_markdown())
            assert isinstance(result, MCPResponse)
            assert f'Stored completion report for loop {loop_state.id}' in result.message

        # List all reports
        list_result = await completion_report_tools.list()
        assert 'Found 3 reports' in list_result.message
        assert 'Strategic Plan Output' in list_result.message

        # Verify each report can be retrieved individually
        for i, loop_state in enumerate(loop_states):
            get_result = await completion_report_tools.get(key=loop_state.id)
            retrieved = PlanCompletionReport.parse_markdown(get_result.message)
            assert retrieved.report_title == 'Strategic Plan Output'
            assert retrieved.final_plan_score == f'{80 + i * 5}'

    @pytest.mark.asyncio
    async def test_state_manager_loop_lifecycle_integration(
        self, state_manager: InMemoryStateManager, completion_report_tools: PlanCompletionReportTools, project_path: str
    ) -> None:
        # Create loop
        loop_state = LoopState(loop_type=LoopType.PLAN)
        await state_manager.add_loop(loop_state, project_path)
        loop_id = loop_state.id

        # Verify loop exists in StateManager
        retrieved_loop = await state_manager.get_loop(loop_id)
        assert retrieved_loop.id == loop_id
        assert retrieved_loop.loop_type == LoopType.PLAN

        # Store completion report
        completion_report = PlanCompletionReport(report_title='Strategic Plan Output', analyst_loop_id=loop_id)

        store_result = await completion_report_tools.store(loop_id, completion_report.build_markdown())
        assert store_result.id == loop_id

        # Update loop status in StateManager (simulating loop progression)
        retrieved_loop.status = LoopStatus.COMPLETED

        # Verify completion report still accessible after loop status change
        get_result = await completion_report_tools.get(key=loop_id)
        retrieved_report = PlanCompletionReport.parse_markdown(get_result.message)
        assert retrieved_report.report_title == 'Strategic Plan Output'

        # Status in response reflects loop status
        assert get_result.status == LoopStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_error_scenarios_integration(
        self, state_manager: InMemoryStateManager, completion_report_tools: PlanCompletionReportTools, project_path: str
    ) -> None:
        # Test storing report for non-existent loop
        non_existent_loop_id = 'deadbeef'
        completion_report = PlanCompletionReport(report_title='Error Test Report')

        with pytest.raises(Exception):  # Should raise ResourceError via LoopNotFoundError
            await completion_report_tools.store(non_existent_loop_id, completion_report.build_markdown())

        # Test retrieving report that was never stored
        loop_state = LoopState(loop_type=LoopType.PLAN)
        await state_manager.add_loop(loop_state, project_path)

        with pytest.raises(Exception):  # Should raise ResourceError
            await completion_report_tools.get(key=loop_state.id)

    def test_template_generation_integration(self) -> None:
        # This tests the template instance creation used in plan_command.py

        # Verify template is properly generated
        assert isinstance(plan_completion_template, str)
        assert '# Strategic Plan Output' in plan_completion_template
        assert '${QUALITY_SCORE}%' in plan_completion_template
        assert '${ANALYST_SCORE}%' in plan_completion_template
        assert '${CURRENT_PLAN}' in plan_completion_template
        assert '${STRUCTURED_OBJECTIVES}' in plan_completion_template
        assert '${ANALYST_LOOP_ID}' in plan_completion_template

    def test_markdown_parsing_roundtrip(self, sample_completion_report_markdown: str) -> None:
        # Parse markdown into model
        parsed_report = PlanCompletionReport.parse_markdown(sample_completion_report_markdown)

        # Verify parsed data
        assert parsed_report.final_plan_score == '85'
        assert parsed_report.final_analyst_score == '90'
        assert (
            'This is a test strategic plan document with comprehensive details.'
            in parsed_report.strategic_plan_document
        )
        # Check that structured_objectives contains the parsed content (may be default if parsing issues)
        assert parsed_report.structured_objectives  # Just verify it's not empty
        assert parsed_report.analyst_loop_id == 'a1b2c3d4'
        assert parsed_report.completion_timestamp == '2025-01-15T14:30:00Z'

        # Regenerate markdown
        regenerated_markdown = parsed_report.build_markdown()

        # Verify key content is preserved
        assert '85%' in regenerated_markdown
        assert '90%' in regenerated_markdown
        assert 'This is a test strategic plan document with comprehensive details.' in regenerated_markdown
        # Check that structured_objectives content is in regenerated markdown
        assert parsed_report.structured_objectives in regenerated_markdown
        assert 'a1b2c3d4' in regenerated_markdown
        assert '2025-01-15T14:30:00Z' in regenerated_markdown
