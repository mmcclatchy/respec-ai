import pytest
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.plan_tools import PlanTools
from src.utils.enums import LoopStatus
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager(max_history_size=3)


@pytest.fixture
def plan_tools(state_manager: InMemoryStateManager) -> PlanTools:
    return PlanTools(state_manager)


def create_plan_markdown(name: str = 'AI-Powered Customer Support System') -> str:
    return f"""# Plan Plan: {name}

## Vision & Mission

### Project Vision
Transform {name.lower()} with automation

### Project Mission
Deliver instant, accurate {name.lower()}

## Timeline & Budget

### Project Timeline
Q2 2024 completion

### Project Budget
$500K development budget

## Objectives & Success Criteria

### Primary Objectives
Reduce response time by 60%, improve satisfaction by 40%

### Success Metrics
Response time < 2 hours, CSAT > 90%

### Key Performance Indicators
Average response time, CSAT score, automation rate

## Scope Definition

### Included Features
AI chatbot, ticket routing, knowledge base

### Excluded Features
Video chat, phone support, multilingual

### Project Assumptions
Support volume remains stable

### Project Constraints
Budget, timeline, team size limitations

## Stakeholders

### Project Sponsor
VP of Customer Success

### Key Stakeholders
Support team, Engineering, Product

### End Users
Customer support agents, customers

## Work Structure

### Work Breakdown
Phase 1: Core AI, Phase 2: Integration, Phase 3: Optimization

### Phases Overview
3 phases over 6 months

### Project Dependencies
AI service, existing CRM system

## Resource & Technology

### Team Structure
3 engineers, 1 designer, 1 PM

### Technology Requirements
Python, FastAPI, OpenAI API

### Infrastructure Needs
Cloud hosting, database, monitoring

## Risk Management

### Identified Risks
Technical complexity, timeline pressure

### Mitigation Strategies
Prototype early, weekly reviews

### Contingency Plans
Reduce scope if needed

## Quality & Testing

### Quality Standards
95% test coverage, code reviews

### Testing Strategy
Unit, integration, user acceptance testing

### Acceptance Criteria
All features working, performance targets met

## Governance

### Reporting Structure
Weekly team updates, monthly stakeholder reports

### Meeting Schedule
Daily standups, weekly planning

### Documentation Standards
API docs, user guides, technical phases

## Metadata

### Status
draft
"""


@pytest.fixture
def sample_plan_markdown() -> str:
    return create_plan_markdown()


class TestPlanToolsStore:
    @pytest.mark.asyncio
    async def test_store_creates_plan(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        key = 'ai-customer-support'

        response = await plan_tools.store(key, sample_plan_markdown)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.IN_PROGRESS
        assert response.id == key

    @pytest.mark.asyncio
    async def test_store_validates_empty_key(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await plan_tools.store('', sample_plan_markdown)

    @pytest.mark.asyncio
    async def test_store_validates_empty_content(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await plan_tools.store('some-key', '')

    @pytest.mark.asyncio
    async def test_store_validates_invalid_markdown(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ToolError, match='Failed to store plan'):
            await plan_tools.store('test-key', 'not valid plan markdown')


class TestPlanToolsGet:
    @pytest.mark.asyncio
    async def test_get_returns_markdown(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        key = 'ai-customer-support'
        await plan_tools.store(key, sample_plan_markdown)

        response = await plan_tools.get(key=key)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert response.id == key
        assert '# Plan:' in response.message
        assert 'AI-Powered Customer Support System' in response.message

    @pytest.mark.asyncio
    async def test_get_raises_error_when_not_found(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ResourceError, match='plan not found'):
            await plan_tools.get(key='non-existent-plan')

    @pytest.mark.asyncio
    async def test_get_requires_key(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ToolError, match='Key is required for plans'):
            await plan_tools.get(key=None)

    @pytest.mark.asyncio
    async def test_get_rejects_loop_id(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        key = 'ai-customer-support'
        await plan_tools.store(key, sample_plan_markdown)

        with pytest.raises(ToolError, match='Plans do not support loop-based retrieval'):
            await plan_tools.get(key=key, loop_id='a1b2c3d4')


class TestPlanToolsList:
    @pytest.mark.asyncio
    async def test_list_returns_empty_for_no_plans(self, plan_tools: PlanTools) -> None:
        response = await plan_tools.list()

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert 'No project plans found' in response.message

    @pytest.mark.asyncio
    async def test_list_returns_multiple_plans(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        await plan_tools.store('plan-1', sample_plan_markdown)

        plan2_markdown = create_plan_markdown('E-commerce Analytics Platform')
        await plan_tools.store('plan-2', plan2_markdown)

        response = await plan_tools.list()

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert 'Found 2 plan' in response.message
        assert 'plan-1' in response.message
        assert 'plan-2' in response.message

    @pytest.mark.asyncio
    async def test_list_ignores_parent_key(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        await plan_tools.store('plan-1', sample_plan_markdown)

        response = await plan_tools.list(parent_key='ignored-value')

        assert isinstance(response, MCPResponse)
        assert 'Found 1 plan' in response.message


class TestPlanToolsUpdate:
    @pytest.mark.asyncio
    async def test_update_modifies_plan(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        key = 'ai-customer-support'
        await plan_tools.store(key, sample_plan_markdown)

        updated_markdown = create_plan_markdown('Updated Plan Name')
        response = await plan_tools.update(key, updated_markdown)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.IN_PROGRESS
        assert response.id == key

        get_response = await plan_tools.get(key=key)
        assert 'Updated Plan Name' in get_response.message

    @pytest.mark.asyncio
    async def test_update_validates_empty_key(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await plan_tools.update('', sample_plan_markdown)

    @pytest.mark.asyncio
    async def test_update_validates_empty_content(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ToolError, match='Key and content cannot be empty'):
            await plan_tools.update('some-key', '')


class TestPlanToolsDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_plan(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        key = 'ai-customer-support'
        await plan_tools.store(key, sample_plan_markdown)

        response = await plan_tools.delete(key)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.COMPLETED
        assert response.id == key
        assert 'Deleted project plan' in response.message

        with pytest.raises(ResourceError):
            await plan_tools.get(key=key)

    @pytest.mark.asyncio
    async def test_delete_raises_error_when_not_found(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ResourceError, match='plan not found'):
            await plan_tools.delete('non-existent-plan')

    @pytest.mark.asyncio
    async def test_delete_validates_empty_key(self, plan_tools: PlanTools) -> None:
        with pytest.raises(ToolError, match='Key cannot be empty'):
            await plan_tools.delete('')


class TestPlanToolsLinkLoop:
    @pytest.mark.asyncio
    async def test_link_loop_raises_error(self, plan_tools: PlanTools, sample_plan_markdown: str) -> None:
        key = 'ai-customer-support'
        await plan_tools.store(key, sample_plan_markdown)

        with pytest.raises(ToolError, match='Plans do not support loop linking'):
            await plan_tools.link_loop('a1b2c3d4', key)
