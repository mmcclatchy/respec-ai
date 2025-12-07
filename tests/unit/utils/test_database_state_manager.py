import pytest

from src.models.enums import ProjectStatus, RoadmapStatus, SpecStatus
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec
from src.utils.enums import LoopType
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    ProjectPlanNotFoundError,
    RoadmapNotFoundError,
    SpecNotFoundError,
)
from src.utils.loop_state import LoopState
from src.utils.state_manager import PostgresStateManager


@pytest.fixture
def project_name() -> str:
    return 'test-project'


@pytest.fixture
def sample_roadmap() -> Roadmap:
    return Roadmap(
        project_name='Test Roadmap',
        project_goal='Test goal',
        total_duration='8 weeks',
        team_size='4 developers',
        roadmap_budget='$100,000',
        critical_path_analysis='Test analysis',
        key_risks='Test risks',
        mitigation_plans='Test mitigation',
        buffer_time='1 week',
        development_resources='4 developers',
        infrastructure_requirements='Cloud hosting',
        external_dependencies='None',
        quality_assurance_plan='Automated testing',
        technical_milestones='MVP delivery',
        business_milestones='User acceptance',
        quality_gates='All tests pass',
        performance_targets='Fast response',
        roadmap_status=RoadmapStatus.DRAFT,
    )


@pytest.fixture
def sample_spec() -> TechnicalSpec:
    return TechnicalSpec(
        phase_name='Sample Spec',
        objectives='Test objectives',
        scope='Test scope',
        dependencies='Test dependencies',
        deliverables='Test deliverables',
        spec_status=SpecStatus.DRAFT,
    )


@pytest.fixture
def sample_loop() -> LoopState:
    return LoopState(loop_type=LoopType.SPEC)


class TestDatabaseRoadmapOperations:
    @pytest.mark.asyncio
    async def test_store_roadmap_returns_project_name(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'

        result = await db_state_manager.store_roadmap(project_name, sample_roadmap)

        assert result == project_name

    @pytest.mark.asyncio
    async def test_store_roadmap_makes_retrievable(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'

        await db_state_manager.store_roadmap(project_name, sample_roadmap)
        retrieved_roadmap = await db_state_manager.get_roadmap(project_name)

        assert retrieved_roadmap == sample_roadmap
        assert retrieved_roadmap.project_name == 'Test Roadmap'

    @pytest.mark.asyncio
    async def test_get_roadmap_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError) as exc_info:
            await db_state_manager.get_roadmap('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_roadmap_overwrites_existing(self, db_state_manager: PostgresStateManager) -> None:
        project_name = 'same-project'
        original_roadmap = Roadmap(
            project_name='Original',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            critical_path_analysis='Test analysis',
            key_risks='Test risks',
            mitigation_plans='Test mitigation',
            buffer_time='1 week',
            development_resources='4 developers',
            infrastructure_requirements='Cloud hosting',
            external_dependencies='None',
            quality_assurance_plan='Automated testing',
            technical_milestones='MVP delivery',
            business_milestones='User acceptance',
            quality_gates='All tests pass',
            performance_targets='Fast response',
            roadmap_status=RoadmapStatus.DRAFT,
        )
        updated_roadmap = Roadmap(
            project_name='Updated',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            critical_path_analysis='Test analysis',
            key_risks='Test risks',
            mitigation_plans='Test mitigation',
            buffer_time='1 week',
            development_resources='4 developers',
            infrastructure_requirements='Cloud hosting',
            external_dependencies='None',
            quality_assurance_plan='Automated testing',
            technical_milestones='MVP delivery',
            business_milestones='User acceptance',
            quality_gates='All tests pass',
            performance_targets='Fast response',
            roadmap_status=RoadmapStatus.DRAFT,
        )

        await db_state_manager.store_roadmap(project_name, original_roadmap)
        await db_state_manager.store_roadmap(project_name, updated_roadmap)

        retrieved = await db_state_manager.get_roadmap(project_name)
        assert retrieved.project_name == 'Updated'

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'project_name,roadmap_name',
        [
            ('proj-1', 'Roadmap 1'),
            ('project-with-dashes', 'Complex Project Roadmap'),
            ('123', 'Numeric Project'),
        ],
    )
    async def test_roadmap_storage_with_various_ids(
        self, db_state_manager: PostgresStateManager, project_name: str, roadmap_name: str
    ) -> None:
        roadmap = Roadmap(
            project_name=roadmap_name,
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            critical_path_analysis='Test analysis',
            key_risks='Test risks',
            mitigation_plans='Test mitigation',
            buffer_time='1 week',
            development_resources='4 developers',
            infrastructure_requirements='Cloud hosting',
            external_dependencies='None',
            quality_assurance_plan='Automated testing',
            technical_milestones='MVP delivery',
            business_milestones='User acceptance',
            quality_gates='All tests pass',
            performance_targets='Fast response',
            roadmap_status=RoadmapStatus.DRAFT,
        )

        stored_id = await db_state_manager.store_roadmap(project_name, roadmap)
        retrieved = await db_state_manager.get_roadmap(project_name)

        assert stored_id == project_name
        assert retrieved.project_name == roadmap_name


class TestDatabaseSpecOperations:
    @pytest.mark.asyncio
    async def test_store_spec_initializes_project_storage(
        self, db_state_manager: PostgresStateManager, sample_spec: TechnicalSpec
    ) -> None:
        result = await db_state_manager.store_spec('new-project', sample_spec)
        assert result == sample_spec.phase_name

        retrieved = await db_state_manager.get_spec('new-project', sample_spec.phase_name)
        assert retrieved.phase_name == sample_spec.phase_name

    @pytest.mark.asyncio
    async def test_store_spec_returns_spec_name(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)

        result = await db_state_manager.store_spec(project_name, sample_spec)

        assert result == sample_spec.phase_name

    @pytest.mark.asyncio
    async def test_store_spec_makes_retrievable(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)

        await db_state_manager.store_spec(project_name, sample_spec)
        retrieved_spec = await db_state_manager.get_spec(project_name, sample_spec.phase_name)

        assert retrieved_spec == sample_spec
        assert retrieved_spec.objectives == 'Test objectives'

    @pytest.mark.asyncio
    async def test_get_spec_raises_error_when_spec_not_found_in_project(
        self, db_state_manager: PostgresStateManager, sample_spec: TechnicalSpec
    ) -> None:
        await db_state_manager.store_spec('test-project', sample_spec)

        with pytest.raises(SpecNotFoundError, match='Spec not found'):
            await db_state_manager.get_spec('test-project', 'nonexistent-spec')

    @pytest.mark.asyncio
    async def test_get_spec_raises_error_when_spec_not_found(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)

        with pytest.raises(SpecNotFoundError):
            await db_state_manager.get_spec(project_name, 'non-existent-spec')

    @pytest.mark.asyncio
    async def test_list_specs_returns_empty_for_empty_roadmap(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'empty-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)

        spec_names = await db_state_manager.list_specs(project_name)

        assert spec_names == []

    @pytest.mark.asyncio
    async def test_list_specs_returns_all_spec_names(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'multi-spec-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)

        spec1 = TechnicalSpec(
            phase_name='spec-1',
            objectives='Obj 1',
            scope='Scope 1',
            dependencies='Dep 1',
            deliverables='Del 1',
            spec_status=SpecStatus.DRAFT,
        )
        spec2 = TechnicalSpec(
            phase_name='spec-2',
            objectives='Obj 2',
            scope='Scope 2',
            dependencies='Dep 2',
            deliverables='Del 2',
            spec_status=SpecStatus.DRAFT,
        )

        await db_state_manager.store_spec(project_name, spec1)
        await db_state_manager.store_spec(project_name, spec2)

        spec_names = await db_state_manager.list_specs(project_name)

        assert len(spec_names) == 2
        assert 'spec-1' in spec_names
        assert 'spec-2' in spec_names

    @pytest.mark.asyncio
    async def test_list_specs_returns_empty_for_project_without_specs(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        result = await db_state_manager.list_specs('project-without-specs')
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_spec_returns_true_when_spec_exists(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)
        await db_state_manager.store_spec(project_name, sample_spec)

        result = await db_state_manager.delete_spec(project_name, sample_spec.phase_name)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_spec_removes_spec_from_roadmap(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)
        await db_state_manager.store_spec(project_name, sample_spec)

        await db_state_manager.delete_spec(project_name, sample_spec.phase_name)

        with pytest.raises(SpecNotFoundError):
            await db_state_manager.get_spec(project_name, sample_spec.phase_name)

    @pytest.mark.asyncio
    async def test_delete_spec_returns_false_when_spec_not_found(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'
        await db_state_manager.store_roadmap(project_name, sample_roadmap)

        result = await db_state_manager.delete_spec(project_name, 'non-existent-spec')

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_spec_returns_false_for_nonexistent_project(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        result = await db_state_manager.delete_spec('nonexistent-project', 'nonexistent-spec')
        assert result is False


class TestDatabaseLoopOperations:
    @pytest.mark.asyncio
    async def test_add_loop_stores_loop_state(
        self, db_state_manager: PostgresStateManager, project_name: str, sample_loop: LoopState
    ) -> None:
        await db_state_manager.add_loop(sample_loop, project_name)

        retrieved_loop = await db_state_manager.get_loop(sample_loop.id)
        assert retrieved_loop == sample_loop

    @pytest.mark.asyncio
    async def test_add_loop_raises_error_for_duplicate_id(
        self, db_state_manager: PostgresStateManager, project_name: str, sample_loop: LoopState
    ) -> None:
        await db_state_manager.add_loop(sample_loop, project_name)

        duplicate_loop = LoopState(loop_type=LoopType.PLAN)
        duplicate_loop.id = sample_loop.id

        with pytest.raises(LoopAlreadyExistsError):
            await db_state_manager.add_loop(duplicate_loop, project_name)

    @pytest.mark.asyncio
    async def test_get_loop_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(LoopNotFoundError):
            await db_state_manager.get_loop('non-existent-loop-id')

    @pytest.mark.asyncio
    async def test_loop_history_management_respects_max_size(
        self, db_state_manager: PostgresStateManager, project_name: str
    ) -> None:
        loops = [
            LoopState(loop_type=LoopType.PLAN),
            LoopState(loop_type=LoopType.SPEC),
            LoopState(loop_type=LoopType.BUILD_PLAN),
            LoopState(loop_type=LoopType.BUILD_CODE),
        ]

        for loop in loops:
            await db_state_manager.add_loop(loop, project_name)

        with pytest.raises(LoopNotFoundError):
            await db_state_manager.get_loop(loops[0].id)

        for loop in loops[1:]:
            retrieved = await db_state_manager.get_loop(loop.id)
            assert retrieved == loop


class TestDatabaseProjectPlanOperations:
    @pytest.mark.asyncio
    async def test_store_project_plan_returns_project_name(self, db_state_manager: PostgresStateManager) -> None:
        project_name = 'test-project'
        project_plan = ProjectPlan(
            project_name=project_name,
            project_vision='Test vision',
            project_mission='Test mission',
            project_timeline='Q1 2024',
            project_budget='$100K',
            primary_objectives='Test objectives',
            success_metrics='Test metrics',
            key_performance_indicators='Test KPIs',
            included_features='Feature A, Feature B',
            excluded_features='Feature C',
            project_assumptions='Test assumptions',
            project_constraints='Test constraints',
            project_sponsor='Test sponsor',
            key_stakeholders='Stakeholder A, Stakeholder B',
            end_users='End users',
            work_breakdown='Phase 1, Phase 2',
            phases_overview='2 phases',
            project_dependencies='Dependency A',
            team_structure='3 developers',
            technology_requirements='Python, FastAPI',
            infrastructure_needs='Cloud hosting',
            identified_risks='Risk A',
            mitigation_strategies='Strategy A',
            contingency_plans='Plan A',
            quality_standards='High quality',
            testing_strategy='Unit and integration tests',
            acceptance_criteria='All tests pass',
            reporting_structure='Weekly updates',
            meeting_schedule='Daily standups',
            documentation_standards='Standard docs',
            project_status=ProjectStatus.DRAFT,
        )

        result = await db_state_manager.store_project_plan(project_name, project_plan)

        assert result == project_name

    @pytest.mark.asyncio
    async def test_store_project_plan_makes_retrievable(self, db_state_manager: PostgresStateManager) -> None:
        project_name = 'test-project'
        project_plan = ProjectPlan(
            project_name=project_name,
            project_vision='Test vision',
            project_mission='Test mission',
            project_timeline='Q1 2024',
            project_budget='$100K',
            primary_objectives='Test objectives',
            success_metrics='Test metrics',
            key_performance_indicators='Test KPIs',
            included_features='Feature A',
            excluded_features='Feature B',
            project_assumptions='Test assumptions',
            project_constraints='Test constraints',
            project_sponsor='Test sponsor',
            key_stakeholders='Stakeholders',
            end_users='Users',
            work_breakdown='Phases',
            phases_overview='Overview',
            project_dependencies='Dependencies',
            team_structure='Team',
            technology_requirements='Tech',
            infrastructure_needs='Infrastructure',
            identified_risks='Risks',
            mitigation_strategies='Strategies',
            contingency_plans='Plans',
            quality_standards='Standards',
            testing_strategy='Testing',
            acceptance_criteria='Criteria',
            reporting_structure='Reporting',
            meeting_schedule='Meetings',
            documentation_standards='Docs',
            project_status=ProjectStatus.DRAFT,
        )

        await db_state_manager.store_project_plan(project_name, project_plan)
        retrieved_plan = await db_state_manager.get_project_plan(project_name)

        assert retrieved_plan == project_plan
        assert retrieved_plan.project_name == project_name
        assert retrieved_plan.project_vision == 'Test vision'

    @pytest.mark.asyncio
    async def test_get_project_plan_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(ProjectPlanNotFoundError) as exc_info:
            await db_state_manager.get_project_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_project_plans_returns_empty_for_no_plans(self, db_state_manager: PostgresStateManager) -> None:
        result = await db_state_manager.list_project_plans()

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_project_plan_returns_true_when_plan_exists(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        project_name = 'test-project'
        project_plan = ProjectPlan(
            project_name=project_name,
            project_vision='Test vision',
            project_mission='Test mission',
            project_timeline='Q1 2024',
            project_budget='$100K',
            primary_objectives='Test objectives',
            success_metrics='Test metrics',
            key_performance_indicators='Test KPIs',
            included_features='Features',
            excluded_features='Excluded',
            project_assumptions='Assumptions',
            project_constraints='Constraints',
            project_sponsor='Sponsor',
            key_stakeholders='Stakeholders',
            end_users='Users',
            work_breakdown='Breakdown',
            phases_overview='Overview',
            project_dependencies='Dependencies',
            team_structure='Team',
            technology_requirements='Tech',
            infrastructure_needs='Infrastructure',
            identified_risks='Risks',
            mitigation_strategies='Strategies',
            contingency_plans='Plans',
            quality_standards='Standards',
            testing_strategy='Testing',
            acceptance_criteria='Criteria',
            reporting_structure='Reporting',
            meeting_schedule='Meetings',
            documentation_standards='Docs',
            project_status=ProjectStatus.DRAFT,
        )

        await db_state_manager.store_project_plan(project_name, project_plan)
        result = await db_state_manager.delete_project_plan(project_name)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_project_plan_removes_plan(self, db_state_manager: PostgresStateManager) -> None:
        project_name = 'test-project'
        project_plan = ProjectPlan(
            project_name=project_name,
            project_vision='Test vision',
            project_mission='Test mission',
            project_timeline='Q1 2024',
            project_budget='$100K',
            primary_objectives='Test objectives',
            success_metrics='Test metrics',
            key_performance_indicators='Test KPIs',
            included_features='Features',
            excluded_features='Excluded',
            project_assumptions='Assumptions',
            project_constraints='Constraints',
            project_sponsor='Sponsor',
            key_stakeholders='Stakeholders',
            end_users='Users',
            work_breakdown='Breakdown',
            phases_overview='Overview',
            project_dependencies='Dependencies',
            team_structure='Team',
            technology_requirements='Tech',
            infrastructure_needs='Infrastructure',
            identified_risks='Risks',
            mitigation_strategies='Strategies',
            contingency_plans='Plans',
            quality_standards='Standards',
            testing_strategy='Testing',
            acceptance_criteria='Criteria',
            reporting_structure='Reporting',
            meeting_schedule='Meetings',
            documentation_standards='Docs',
            project_status=ProjectStatus.DRAFT,
        )

        await db_state_manager.store_project_plan(project_name, project_plan)
        await db_state_manager.delete_project_plan(project_name)

        with pytest.raises(ProjectPlanNotFoundError):
            await db_state_manager.get_project_plan(project_name)

    @pytest.mark.asyncio
    async def test_delete_project_plan_raises_error_when_not_found(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        with pytest.raises(ProjectPlanNotFoundError) as exc_info:
            await db_state_manager.delete_project_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)
