import pytest
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.plan_completion_report_tools import PlanCompletionReportTools
from src.models.plan_completion_report import PlanCompletionReport
from src.utils.enums import LoopStatus, LoopType
from src.utils.loop_state import LoopState, MCPResponse
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def project_path() -> str:
    return '/tmp/test-project'


class TestPlanCompletionReportTools:
    @pytest.fixture
    def real_state_manager(self) -> InMemoryStateManager:
        return InMemoryStateManager()

    @pytest.fixture
    def completion_report_tools(self, real_state_manager: InMemoryStateManager) -> PlanCompletionReportTools:
        return PlanCompletionReportTools(real_state_manager)

    @pytest.fixture
    def sample_completion_report(self) -> PlanCompletionReport:
        return PlanCompletionReport(
            report_title='Strategic Plan Output',
            final_plan_score='85',
            final_analyst_score='90',
            strategic_plan_document='# Test Plan\nContent here',
            structured_objectives='Test objectives',
            analyst_loop_id='a1b2c3d4',
        )

    @pytest.fixture
    def sample_loop_state(self) -> LoopState:
        return LoopState(loop_type=LoopType.PLAN)

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

# Test Plan
Content here

## Structured Objectives

Test objectives

## Next Steps

1. Review the strategic plan
2. Proceed with Phase creation

## Metadata

### Analyst Loop ID
a1b2c3d4

### Timestamp
2024-01-15
"""

    @pytest.fixture
    def updated_completion_report_markdown(self) -> str:
        return """# Strategic Plan Output

## Plan Quality

### Final Plan Score
95

### Plan Completion Status
User-accepted (human-driven decision)

### User Decision
accept_plan

## Analyst Validation

### Final Analyst Score
98

### Analyst Completion Status
completed

### Analyst Loop Result
completed

## Strategic Plan Document

# Updated Plan
New content here

## Structured Objectives

Updated objectives

## Next Steps

1. Updated review steps

## Metadata

### Analyst Loop ID
b2c3d4e5

### Timestamp
2024-01-20
"""

    # Test store method

    @pytest.mark.asyncio
    async def test_store_success(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)

        result = await completion_report_tools.store(loop_id, sample_completion_report_markdown)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert result.status == sample_loop_state.status
        assert f'Stored completion report for loop {loop_id}' in result.message

    @pytest.mark.asyncio
    async def test_store_empty_key(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
    ) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await completion_report_tools.store('', sample_completion_report_markdown)

    @pytest.mark.asyncio
    async def test_store_empty_content(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await completion_report_tools.store('a1b2c3d4', '')

    @pytest.mark.asyncio
    async def test_store_loop_not_found(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
    ) -> None:
        with pytest.raises(ResourceError, match='Loop does not exist'):
            await completion_report_tools.store('deadbeef', sample_completion_report_markdown)

    # Test get method

    @pytest.mark.asyncio
    async def test_get_success_with_key(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)
        await completion_report_tools.store(loop_id, sample_completion_report_markdown)

        result = await completion_report_tools.get(key=loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert '# Strategic Plan Output' in result.message

    @pytest.mark.asyncio
    async def test_get_success_with_loop_id(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)
        await completion_report_tools.store(loop_id, sample_completion_report_markdown)

        result = await completion_report_tools.get(loop_id=loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert '# Strategic Plan Output' in result.message

    @pytest.mark.asyncio
    async def test_get_no_key_or_loop_id(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        with pytest.raises(ToolError, match='Either key OR loop_id must be provided'):
            await completion_report_tools.get()

    @pytest.mark.asyncio
    async def test_get_not_found(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)

        with pytest.raises(ResourceError, match='No completion report stored for this loop'):
            await completion_report_tools.get(key=loop_id)

    @pytest.mark.asyncio
    async def test_get_loop_not_found(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        with pytest.raises(ResourceError, match='Loop does not exist'):
            await completion_report_tools.get(key='deadbeef')

    # Test list method

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        result = await completion_report_tools.list()
        assert isinstance(result, MCPResponse)
        assert 'No completion reports found' in result.message

    @pytest.mark.asyncio
    async def test_list_with_data(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)
        await completion_report_tools.store(loop_id, sample_completion_report_markdown)

        result = await completion_report_tools.list()
        assert isinstance(result, MCPResponse)
        assert 'Found 1 report' in result.message
        assert 'Strategic Plan Output' in result.message

    # Test update method

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        updated_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)
        await completion_report_tools.store(loop_id, sample_completion_report_markdown)

        result = await completion_report_tools.update(loop_id, updated_completion_report_markdown)

        assert isinstance(result, MCPResponse)
        assert f'Updated completion report for loop {loop_id}' in result.message

    @pytest.mark.asyncio
    async def test_update_empty_key(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
    ) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await completion_report_tools.update('', sample_completion_report_markdown)

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)

        with pytest.raises(ResourceError, match='No completion report stored for this loop'):
            await completion_report_tools.update(loop_id, sample_completion_report_markdown)

    # Test delete method

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        completion_report_tools: PlanCompletionReportTools,
        sample_completion_report_markdown: str,
        sample_loop_state: LoopState,
        project_path: str,
    ) -> None:
        loop_id = sample_loop_state.id
        await completion_report_tools.state.add_loop(sample_loop_state, project_path)
        await completion_report_tools.store(loop_id, sample_completion_report_markdown)

        result = await completion_report_tools.delete(loop_id)
        assert isinstance(result, MCPResponse)
        assert 'Deleted completion report' in result.message

    @pytest.mark.asyncio
    async def test_delete_empty_key(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        with pytest.raises(ToolError, match='Key cannot be empty'):
            await completion_report_tools.delete('')

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        with pytest.raises(ResourceError, match='No completion report found'):
            await completion_report_tools.delete('deadbeef')

    # Test link_loop method

    @pytest.mark.asyncio
    async def test_link_loop_success(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        loop_id = 'a1b2c3d4'

        result = await completion_report_tools.link_loop(loop_id, loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert result.status == LoopStatus.COMPLETED
        assert 'already linked' in result.message

    @pytest.mark.asyncio
    async def test_link_loop_mismatch(
        self,
        completion_report_tools: PlanCompletionReportTools,
    ) -> None:
        with pytest.raises(ToolError, match='For completion reports, loop_id must equal key'):
            await completion_report_tools.link_loop('a1b2c3d4', 'b2c3d4e5')
