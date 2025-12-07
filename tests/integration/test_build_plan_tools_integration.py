import pytest
from src.mcp.tools.build_plan_tools import BuildPlanTools
from src.mcp.tools.loop_tools import LoopTools
from src.models.build_plan import BuildPlan
from src.models.enums import BuildStatus
from src.utils.enums import LoopStatus
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def project_name() -> str:
    return 'test-project'


class TestBuildPlanToolsIntegration:
    @pytest.mark.asyncio
    async def test_store_build_plan_end_to_end(self, project_name: str) -> None:
        state_manager = InMemoryStateManager()
        build_plan_tools = BuildPlanTools(state_manager)
        loop_tools = LoopTools(state_manager)

        loop_response = await loop_tools.initialize_refinement_loop(project_name, 'build_plan')
        loop_id = loop_response.id

        build_plan = BuildPlan(
            project_name='E-Commerce Platform',
            project_goal='Build scalable online marketplace',
            total_duration='6 months development cycle',
            team_size='8 developers, 2 QA, 1 DevOps',
            primary_language='TypeScript for full-stack development',
            framework='React 18 with Next.js for frontend, Node.js with Express',
            database='PostgreSQL with Redis for caching',
            development_environment='Docker containers with hot-reload',
            database_schema='Normalized schema with user, product, order entities',
            api_architecture='RESTful API with GraphQL for complex queries',
            frontend_architecture='Component-based with state management',
            core_features='User auth, product catalog, shopping cart, payment',
            integration_points='Payment gateway, shipping API, inventory system',
            testing_strategy='Jest for unit tests, Cypress for E2E',
            code_standards='ESLint with TypeScript, Prettier formatting',
            performance_requirements='<200ms API response, <2s page load',
            security_implementation='JWT auth, input validation, HTTPS',
            build_status=BuildStatus.PLANNING,
        )

        result = await build_plan_tools.store_build_plan(loop_id, build_plan)

        assert result.id == loop_id
        assert result.status in [LoopStatus.INITIALIZED, LoopStatus.IN_PROGRESS]
        assert 'E-Commerce Platform' in result.message

        stored_plan = await build_plan_tools.get_build_plan_data(loop_id)
        assert stored_plan.project_name == 'E-Commerce Platform'
        assert stored_plan.project_goal == 'Build scalable online marketplace'

    @pytest.mark.asyncio
    async def test_get_build_plan_markdown_integration(self, project_name: str) -> None:
        state_manager = InMemoryStateManager()
        build_plan_tools = BuildPlanTools(state_manager)
        loop_tools = LoopTools(state_manager)

        loop_response = await loop_tools.initialize_refinement_loop(project_name, 'build_plan')
        loop_id = loop_response.id

        build_plan = BuildPlan(
            project_name='API Gateway Service',
            project_goal='Centralized API routing and authentication',
            total_duration='3 months implementation',
            primary_language='Go for high performance',
            framework='Gin web framework with middleware support',
            database='PostgreSQL with connection pooling',
        )

        await build_plan_tools.store_build_plan(loop_id, build_plan)
        result = await build_plan_tools.get_build_plan_markdown(loop_id)

        assert result.id == loop_id
        assert 'API Gateway Service' in result.message
        assert 'Centralized API routing and authentication' in result.message
        assert '## Technology Stack' in result.message
        assert '### Primary Language' in result.message

    @pytest.mark.asyncio
    async def test_list_build_plans_integration(self, project_name: str) -> None:
        state_manager = InMemoryStateManager()
        build_plan_tools = BuildPlanTools(state_manager)
        loop_tools = LoopTools(state_manager)

        plans_data = [
            ('Analytics Dashboard', 'Real-time data visualization platform'),
            ('User Management System', 'Comprehensive user administration'),
            ('Notification Service', 'Multi-channel notification delivery'),
        ]

        for project_name, project_goal in plans_data:
            loop_response = await loop_tools.initialize_refinement_loop(project_name, 'build_plan')
            loop_id = loop_response.id

            build_plan = BuildPlan(
                project_name=project_name,
                project_goal=project_goal,
            )
            await build_plan_tools.store_build_plan(loop_id, build_plan)

        result = await build_plan_tools.list_build_plans(2)
        assert 'Found 2 build plan' in result.message
        assert 'Notification Service' in result.message
        assert 'User Management System' in result.message

    @pytest.mark.asyncio
    async def test_delete_build_plan_integration(self, project_name: str) -> None:
        state_manager = InMemoryStateManager()
        build_plan_tools = BuildPlanTools(state_manager)
        loop_tools = LoopTools(state_manager)

        loop_response = await loop_tools.initialize_refinement_loop(project_name, 'build_plan')
        loop_id = loop_response.id

        build_plan = BuildPlan(
            project_name='Content Management System',
            project_goal='Headless CMS with REST and GraphQL APIs',
        )

        await build_plan_tools.store_build_plan(loop_id, build_plan)
        result = await build_plan_tools.delete_build_plan(loop_id)

        assert result.id == loop_id
        assert 'Content Management System' in result.message

    @pytest.mark.asyncio
    async def test_build_plan_not_found_error(self, project_name: str) -> None:
        state_manager = InMemoryStateManager()
        build_plan_tools = BuildPlanTools(state_manager)
        loop_tools = LoopTools(state_manager)

        loop_response = await loop_tools.initialize_refinement_loop(project_name, 'build_plan')
        loop_id = loop_response.id

        try:
            await build_plan_tools.get_build_plan_data(loop_id)
            assert False, 'Should have raised ResourceError'
        except Exception as e:
            assert 'No build plan stored' in str(e)

    @pytest.mark.asyncio
    async def test_loop_not_found_error(self) -> None:
        state_manager = InMemoryStateManager()
        build_plan_tools = BuildPlanTools(state_manager)

        build_plan = BuildPlan(
            project_name='Invalid Loop Test',
            project_goal='Test error handling',
        )

        try:
            await build_plan_tools.store_build_plan('invalid-loop-id', build_plan)
            assert False, 'Should have raised ResourceError'
        except Exception as e:
            assert 'Loop does not exist' in str(e)
