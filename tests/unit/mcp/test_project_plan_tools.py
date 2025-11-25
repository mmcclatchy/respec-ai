import pytest
from fastmcp.exceptions import ResourceError, ToolError

from services.mcp.tools.project_plan_tools import ProjectPlanTools
from services.models.enums import ProjectStatus
from services.models.project_plan import ProjectPlan
from services.utils.enums import LoopStatus
from services.utils.loop_state import MCPResponse
from services.utils.state_manager import InMemoryStateManager


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager(max_history_size=3)


@pytest.fixture
def project_plan_tools(state_manager: InMemoryStateManager) -> ProjectPlanTools:
    return ProjectPlanTools(state_manager)


def create_project_plan(name: str = 'AI-Powered Customer Support System') -> ProjectPlan:
    return ProjectPlan(
        project_name=name,
        project_vision=f'Transform {name.lower()} with automation',
        project_mission=f'Deliver instant, accurate {name.lower()}',
        project_timeline='Q2 2024 completion',
        project_budget='$500K development budget',
        primary_objectives='Reduce response time by 60%, improve satisfaction by 40%',
        success_metrics='Response time < 2 hours, CSAT > 90%',
        key_performance_indicators='Average response time, CSAT score, automation rate',
        included_features='AI chatbot, ticket routing, knowledge base',
        excluded_features='Video chat, phone support, multilingual',
        project_assumptions='Support volume remains stable',
        project_constraints='Budget, timeline, team size limitations',
        project_sponsor='VP of Customer Success',
        key_stakeholders='Support team, Engineering, Product',
        end_users='Customer support agents, customers',
        work_breakdown='Phase 1: Core AI, Phase 2: Integration, Phase 3: Optimization',
        phases_overview='3 phases over 6 months',
        project_dependencies='AI service, existing CRM system',
        team_structure='3 engineers, 1 designer, 1 PM',
        technology_requirements='Python, FastAPI, OpenAI API',
        infrastructure_needs='Cloud hosting, database, monitoring',
        identified_risks='Technical complexity, timeline pressure',
        mitigation_strategies='Prototype early, weekly reviews',
        contingency_plans='Reduce scope if needed',
        quality_standards='95% test coverage, code reviews',
        testing_strategy='Unit, integration, user acceptance testing',
        acceptance_criteria='All features working, performance targets met',
        reporting_structure='Weekly team updates, monthly stakeholder reports',
        meeting_schedule='Daily standups, weekly planning',
        documentation_standards='API docs, user guides, technical specs',
        project_status=ProjectStatus.DRAFT,
        creation_date='2024-01-01',
        last_updated='2024-01-01',
        version='1.0',
    )


@pytest.fixture
def sample_project_plan() -> ProjectPlan:
    return create_project_plan()


@pytest.fixture
def project_path() -> str:
    return '/tmp/test-project'


class TestProjectPlanTools:
    pass


class TestCreateProjectPlan:
    def test_create_project_plan_creates_new_project_entry(
        self, project_plan_tools: ProjectPlanTools, sample_project_plan: ProjectPlan
    ) -> None:
        response = project_plan_tools.create_project_plan(sample_project_plan.project_name, sample_project_plan)

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.INITIALIZED
        assert 'Created project plan' in response.message
        assert response.id == sample_project_plan.project_name

        # Verify project plan was stored by project name
        stored_plan = project_plan_tools.get_project_plan_data(sample_project_plan.project_name)
        assert stored_plan.project_name == sample_project_plan.project_name

    def test_create_project_plan_validates_project_plan_model(self, project_plan_tools: ProjectPlanTools) -> None:
        with pytest.raises(ToolError):
            project_plan_tools.create_project_plan('test-project', None)  # type: ignore[arg-type]


class TestStoreProjectPlan:
    def test_store_project_plan_validates_project_plan_model(self, project_plan_tools: ProjectPlanTools) -> None:
        with pytest.raises(ToolError, match='Invalid project plan: ProjectPlan cannot be None'):
            project_plan_tools.store_project_plan('some-project-name', None)  # type: ignore[arg-type]

    def test_store_project_plan_updates_existing_project(
        self,
        project_plan_tools: ProjectPlanTools,
        sample_project_plan: ProjectPlan,
    ) -> None:
        project_name = sample_project_plan.project_name

        response = project_plan_tools.store_project_plan(project_name, sample_project_plan)

        assert response.id == project_name
        assert response.status == LoopStatus.IN_PROGRESS
        assert 'Stored project plan' in response.message

    def test_store_project_plan_stores_structured_data(
        self,
        project_plan_tools: ProjectPlanTools,
        sample_project_plan: ProjectPlan,
    ) -> None:
        project_name = sample_project_plan.project_name

        project_plan_tools.store_project_plan(project_name, sample_project_plan)

        # Verify structured data is stored (not just markdown)
        stored_plan = project_plan_tools.get_project_plan_data(project_name)
        assert stored_plan.project_name == sample_project_plan.project_name
        assert stored_plan.project_vision == sample_project_plan.project_vision
        assert stored_plan.primary_objectives == sample_project_plan.primary_objectives


class TestGetProjectPlan:
    def test_get_project_plan_returns_structured_data(
        self, project_plan_tools: ProjectPlanTools, sample_project_plan: ProjectPlan
    ) -> None:
        # Create plan first
        response = project_plan_tools.create_project_plan(sample_project_plan.project_name, sample_project_plan)

        # Retrieve plan
        retrieved_plan = project_plan_tools.get_project_plan_data(response.id)

        assert isinstance(retrieved_plan, ProjectPlan)
        assert retrieved_plan.project_name == sample_project_plan.project_name
        assert retrieved_plan.project_vision == sample_project_plan.project_vision
        assert retrieved_plan.primary_objectives == sample_project_plan.primary_objectives

    def test_get_project_plan_raises_error_when_project_not_found(self, project_plan_tools: ProjectPlanTools) -> None:
        with pytest.raises(ResourceError) as exc_info:
            project_plan_tools.get_project_plan_data('non-existent-project')

        assert 'Project plan not found for project' in str(exc_info.value)


class TestGetProjectPlanMarkdown:
    def test_get_project_plan_markdown_generates_platform_output(
        self, project_plan_tools: ProjectPlanTools, sample_project_plan: ProjectPlan
    ) -> None:
        response = project_plan_tools.create_project_plan(sample_project_plan.project_name, sample_project_plan)

        markdown_response = project_plan_tools.get_project_plan_markdown(response.id)

        assert isinstance(markdown_response, MCPResponse)
        assert markdown_response.id == response.id
        assert markdown_response.status == LoopStatus.COMPLETED
        assert '# Project Plan:' in markdown_response.message
        assert sample_project_plan.project_name in markdown_response.message
        assert sample_project_plan.project_vision in markdown_response.message

    def test_get_project_plan_markdown_platform_agnostic(
        self, project_plan_tools: ProjectPlanTools, sample_project_plan: ProjectPlan
    ) -> None:
        response = project_plan_tools.create_project_plan(sample_project_plan.project_name, sample_project_plan)

        markdown_response = project_plan_tools.get_project_plan_markdown(response.id)
        assert isinstance(markdown_response, MCPResponse)
        assert sample_project_plan.project_name in markdown_response.message

    def test_get_project_plan_markdown_raises_error_when_project_not_found(
        self, project_plan_tools: ProjectPlanTools
    ) -> None:
        with pytest.raises(ToolError):
            project_plan_tools.get_project_plan_markdown('non-existent-project')


class TestListProjectPlans:
    def test_list_project_plans_returns_empty_for_no_plans(self, project_plan_tools: ProjectPlanTools) -> None:
        response = project_plan_tools.list_project_plans()

        assert isinstance(response, MCPResponse)
        assert response.status == LoopStatus.INITIALIZED
        assert 'No project plans found' in response.message

    def test_list_project_plans_returns_multiple_plans(
        self, project_plan_tools: ProjectPlanTools, sample_project_plan: ProjectPlan
    ) -> None:
        # Store multiple plans
        plan1_response = project_plan_tools.create_project_plan(sample_project_plan.project_name, sample_project_plan)

        plan2 = ProjectPlan(
            project_name='E-commerce Analytics Platform',
            project_vision='Data-driven sales optimization',
            project_mission='Increase conversion through analytics',
            project_timeline='Q3 2024',
            project_budget='$300K',
            primary_objectives='Increase conversion by 25%',
            success_metrics='Conversion rate > 3%',
            key_performance_indicators='Conversion rate, revenue per visit',
            included_features='Dashboard, reports, API',
            excluded_features='Real-time alerts',
            project_assumptions='Historical data available',
            project_constraints='Budget and timeline',
            project_sponsor='VP Sales',
            key_stakeholders='Sales, Marketing',
            end_users='Sales team, analysts',
            work_breakdown='Phase 1: Data, Phase 2: Analytics',
            phases_overview='2 phases over 4 months',
            project_dependencies='Existing CRM data',
            team_structure='2 engineers, 1 analyst',
            technology_requirements='Python, SQL, Tableau',
            infrastructure_needs='Data warehouse, BI tools',
            identified_risks='Data quality issues',
            mitigation_strategies='Data validation processes',
            contingency_plans='Manual reporting fallback',
            quality_standards='Data accuracy > 95%',
            testing_strategy='Unit tests, data validation',
            acceptance_criteria='All KPIs tracked accurately',
            reporting_structure='Weekly reports to VP Sales',
            meeting_schedule='Bi-weekly status updates',
            documentation_standards='Data dictionary, user guides',
            project_status=ProjectStatus.DRAFT,
            creation_date='2024-01-15',
            last_updated='2024-01-15',
            version='1.0',
        )
        plan2_response = project_plan_tools.create_project_plan(plan2.project_name, plan2)

        # List all plans
        response = project_plan_tools.list_project_plans()

        assert 'Found 2 project plans:' in response.message
        assert sample_project_plan.project_name in response.message
        assert plan2.project_name in response.message
        assert plan1_response.id in response.message
        assert plan2_response.id in response.message

    def test_list_project_plans_respects_count_limit(self, project_plan_tools: ProjectPlanTools) -> None:
        # Store 3 plans
        for i in range(3):
            plan = create_project_plan(f'Project {i + 1}')
            project_plan_tools.create_project_plan(plan.project_name, plan)

        # List with limit
        response = project_plan_tools.list_project_plans(count=2)

        assert 'Found 2 project plans:' in response.message
        assert 'Project 2' in response.message
        assert 'Project 3' in response.message
        assert 'Project 1' not in response.message


class TestDeleteProjectPlan:
    def test_delete_project_plan_removes_plan(
        self, project_plan_tools: ProjectPlanTools, sample_project_plan: ProjectPlan
    ) -> None:
        # Store plan first
        response = project_plan_tools.create_project_plan(sample_project_plan.project_name, sample_project_plan)

        # Delete plan
        delete_response = project_plan_tools.delete_project_plan(response.id)

        assert isinstance(delete_response, MCPResponse)
        assert delete_response.id == response.id
        assert 'Deleted project plan' in delete_response.message

        # Verify plan is removed
        with pytest.raises(ResourceError):
            project_plan_tools.get_project_plan_data(response.id)

    def test_delete_project_plan_raises_error_when_project_not_found(
        self, project_plan_tools: ProjectPlanTools
    ) -> None:
        with pytest.raises(ResourceError) as exc_info:
            project_plan_tools.delete_project_plan('non-existent-project')

        assert 'Project plan not found for project' in str(exc_info.value)
