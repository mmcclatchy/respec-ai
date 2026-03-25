import pytest

from src.models.enums import PhaseStatus, PlanStatus, RoadmapStatus
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.utils.enums import LoopType
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    PhaseNotFoundError,
    PlanNotFoundError,
    RoadmapNotFoundError,
)
from src.utils.loop_state import LoopState
from src.utils.state_manager import PostgresStateManager


@pytest.fixture
def plan_name() -> str:
    return 'test-project'


@pytest.fixture
def sample_roadmap() -> Roadmap:
    return Roadmap(
        plan_name='Test Roadmap',
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
def sample_phase() -> Phase:
    return Phase(
        phase_name='sample-phase',
        objectives='Test objectives',
        scope='Test scope',
        dependencies='Test dependencies',
        deliverables='Test deliverables',
        phase_status=PhaseStatus.DRAFT,
    )


@pytest.fixture
def sample_loop() -> LoopState:
    return LoopState(loop_type=LoopType.PHASE)


class TestDatabaseRoadmapOperations:
    @pytest.mark.asyncio
    async def test_store_roadmap_returns_plan_name(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'

        result = await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        assert result == plan_name

    @pytest.mark.asyncio
    async def test_store_roadmap_makes_retrievable(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'

        await db_state_manager.store_roadmap(plan_name, sample_roadmap)
        retrieved_roadmap = await db_state_manager.get_roadmap(plan_name)

        assert retrieved_roadmap == sample_roadmap
        assert retrieved_roadmap.plan_name == 'Test Roadmap'

    @pytest.mark.asyncio
    async def test_get_roadmap_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError) as exc_info:
            await db_state_manager.get_roadmap('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_roadmap_overwrites_existing(self, db_state_manager: PostgresStateManager) -> None:
        plan_name = 'same-project'
        original_roadmap = Roadmap(
            plan_name='Original',
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
            plan_name='Updated',
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

        await db_state_manager.store_roadmap(plan_name, original_roadmap)
        await db_state_manager.store_roadmap(plan_name, updated_roadmap)

        retrieved = await db_state_manager.get_roadmap(plan_name)
        assert retrieved.plan_name == 'Updated'

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'plan_name,roadmap_name',
        [
            ('proj-1', 'Roadmap 1'),
            ('project-with-dashes', 'Complex Plan Roadmap'),
            ('123', 'Numeric Plan'),
        ],
    )
    async def test_roadmap_storage_with_various_ids(
        self, db_state_manager: PostgresStateManager, plan_name: str, roadmap_name: str
    ) -> None:
        roadmap = Roadmap(
            plan_name=roadmap_name,
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

        stored_id = await db_state_manager.store_roadmap(plan_name, roadmap)
        retrieved = await db_state_manager.get_roadmap(plan_name)

        assert stored_id == plan_name
        assert retrieved.plan_name == roadmap_name


class TestDatabaseSpecOperations:
    @pytest.mark.asyncio
    async def test_store_phase_initializes_project_storage(
        self, db_state_manager: PostgresStateManager, sample_phase: Phase
    ) -> None:
        result = await db_state_manager.store_phase('new-project', sample_phase)
        assert result == sample_phase.phase_name

        retrieved = await db_state_manager.get_phase('new-project', sample_phase.phase_name)
        assert retrieved.phase_name == sample_phase.phase_name

    @pytest.mark.asyncio
    async def test_store_phase_returns_phase_name(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        result = await db_state_manager.store_phase(plan_name, sample_phase)

        assert result == sample_phase.phase_name

    @pytest.mark.asyncio
    async def test_store_phase_makes_retrievable(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        await db_state_manager.store_phase(plan_name, sample_phase)
        retrieved_phase = await db_state_manager.get_phase(plan_name, sample_phase.phase_name)

        assert retrieved_phase == sample_phase
        assert retrieved_phase.objectives == 'Test objectives'

    @pytest.mark.asyncio
    async def test_get_phase_raises_error_when_phase_not_found_in_project(
        self, db_state_manager: PostgresStateManager, sample_phase: Phase
    ) -> None:
        await db_state_manager.store_phase('test-project', sample_phase)

        with pytest.raises(PhaseNotFoundError, match='Phase not found'):
            await db_state_manager.get_phase('test-project', 'nonexistent-phase')

    @pytest.mark.asyncio
    async def test_get_phase_raises_error_when_phase_not_found(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        with pytest.raises(PhaseNotFoundError):
            await db_state_manager.get_phase(plan_name, 'non-existent-phase')

    @pytest.mark.asyncio
    async def test_list_phases_returns_empty_for_empty_roadmap(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'empty-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        phase_names = await db_state_manager.list_phases(plan_name)

        assert phase_names == []

    @pytest.mark.asyncio
    async def test_list_phases_returns_all_phase_names(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'multi-phase-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        phase1 = Phase(
            phase_name='phase-1',
            objectives='Obj 1',
            scope='Scope 1',
            dependencies='Dep 1',
            deliverables='Del 1',
            phase_status=PhaseStatus.DRAFT,
        )
        phase2 = Phase(
            phase_name='phase-2',
            objectives='Obj 2',
            scope='Scope 2',
            dependencies='Dep 2',
            deliverables='Del 2',
            phase_status=PhaseStatus.DRAFT,
        )

        await db_state_manager.store_phase(plan_name, phase1)
        await db_state_manager.store_phase(plan_name, phase2)

        phase_names = await db_state_manager.list_phases(plan_name)

        assert len(phase_names) == 2
        assert 'phase-1' in phase_names
        assert 'phase-2' in phase_names

    @pytest.mark.asyncio
    async def test_list_phases_returns_empty_for_project_without_phases(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        result = await db_state_manager.list_phases('project-without-phases')
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_phase_returns_true_when_phase_exists(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)
        await db_state_manager.store_phase(plan_name, sample_phase)

        result = await db_state_manager.delete_phase(plan_name, sample_phase.phase_name)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_phase_removes_phase_from_roadmap(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)
        await db_state_manager.store_phase(plan_name, sample_phase)

        await db_state_manager.delete_phase(plan_name, sample_phase.phase_name)

        with pytest.raises(PhaseNotFoundError):
            await db_state_manager.get_phase(plan_name, sample_phase.phase_name)

    @pytest.mark.asyncio
    async def test_delete_phase_returns_false_when_phase_not_found(
        self, db_state_manager: PostgresStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'
        await db_state_manager.store_roadmap(plan_name, sample_roadmap)

        result = await db_state_manager.delete_phase(plan_name, 'non-existent-phase')

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_phase_returns_false_for_nonexistent_project(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        result = await db_state_manager.delete_phase('nonexistent-project', 'nonexistent-phase')
        assert result is False


class TestDatabaseLoopOperations:
    @pytest.mark.asyncio
    async def test_add_loop_stores_loop_state(
        self, db_state_manager: PostgresStateManager, plan_name: str, sample_loop: LoopState
    ) -> None:
        await db_state_manager.add_loop(sample_loop, plan_name)

        retrieved_loop = await db_state_manager.get_loop(sample_loop.id)
        assert retrieved_loop == sample_loop

    @pytest.mark.asyncio
    async def test_add_loop_raises_error_for_duplicate_id(
        self, db_state_manager: PostgresStateManager, plan_name: str, sample_loop: LoopState
    ) -> None:
        await db_state_manager.add_loop(sample_loop, plan_name)

        duplicate_loop = LoopState(loop_type=LoopType.PLAN)
        duplicate_loop.id = sample_loop.id

        with pytest.raises(LoopAlreadyExistsError):
            await db_state_manager.add_loop(duplicate_loop, plan_name)

    @pytest.mark.asyncio
    async def test_get_loop_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(LoopNotFoundError):
            await db_state_manager.get_loop('non-existent-loop-id')


class TestDatabasePlanOperations:
    @pytest.mark.asyncio
    async def test_store_plan_returns_plan_name(self, db_state_manager: PostgresStateManager) -> None:
        plan_name = 'test-project'
        plan = Plan(
            plan_name=plan_name,
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
            plan_status=PlanStatus.DRAFT,
        )

        result = await db_state_manager.store_plan(plan_name, plan)

        assert result == plan_name

    @pytest.mark.asyncio
    async def test_store_plan_makes_retrievable(self, db_state_manager: PostgresStateManager) -> None:
        plan_name = 'test-project'
        plan = Plan(
            plan_name=plan_name,
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
            plan_status=PlanStatus.DRAFT,
        )

        await db_state_manager.store_plan(plan_name, plan)
        retrieved_plan = await db_state_manager.get_plan(plan_name)

        assert retrieved_plan == plan
        assert retrieved_plan.plan_name == plan_name
        assert retrieved_plan.project_vision == 'Test vision'

    @pytest.mark.asyncio
    async def test_get_plan_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(PlanNotFoundError) as exc_info:
            await db_state_manager.get_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_plans_returns_empty_for_no_plans(self, db_state_manager: PostgresStateManager) -> None:
        result = await db_state_manager.list_plans()

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_plan_returns_true_when_plan_exists(self, db_state_manager: PostgresStateManager) -> None:
        plan_name = 'test-project'
        plan = Plan(
            plan_name=plan_name,
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
            plan_status=PlanStatus.DRAFT,
        )

        await db_state_manager.store_plan(plan_name, plan)
        result = await db_state_manager.delete_plan(plan_name)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_plan_removes_plan(self, db_state_manager: PostgresStateManager) -> None:
        plan_name = 'test-project'
        plan = Plan(
            plan_name=plan_name,
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
            plan_status=PlanStatus.DRAFT,
        )

        await db_state_manager.store_plan(plan_name, plan)
        await db_state_manager.delete_plan(plan_name)

        with pytest.raises(PlanNotFoundError):
            await db_state_manager.get_plan(plan_name)

    @pytest.mark.asyncio
    async def test_delete_plan_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(PlanNotFoundError) as exc_info:
            await db_state_manager.delete_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)
