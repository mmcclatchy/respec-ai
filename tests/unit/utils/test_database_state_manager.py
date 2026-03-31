import pytest

from src.models.enums import PhaseStatus, PlanStatus, RoadmapStatus
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.models.task import Task
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
    @staticmethod
    def _make_plan(name: str = 'test-project', suffix: str = '', status: PlanStatus = PlanStatus.DRAFT) -> Plan:
        s = suffix
        return Plan(
            plan_name=name,
            executive_summary=f'### Vision\nVision{s}\n\n### Budget\n$100K{s}',
            business_objectives=f'### Primary Objectives\nObjectives{s}',
            plan_scope=f'### Included Features\nFeatures{s}\n\n### Constraints\nConstraints{s}',
            stakeholders=f'### Plan Sponsor\nSponsor{s}\n\n### End Users\nUsers{s}',
            architecture_direction=f'### Architecture Overview\nArchitecture{s}',
            technology_decisions=f'### Chosen Technologies\nTech{s}',
            plan_structure=f'### Work Breakdown\nBreakdown{s}',
            resource_requirements=f'### Team Structure\nTeam{s}',
            risk_management=f'### Identified Risks\nRisks{s}',
            quality_assurance=f'### Quality Bar\nStandards{s}',
            plan_status=status,
        )

    @pytest.mark.asyncio
    async def test_store_plan_returns_plan_name(self, db_state_manager: PostgresStateManager) -> None:
        plan = self._make_plan()
        result = await db_state_manager.store_plan('test-project', plan)
        assert result == 'test-project'

    @pytest.mark.asyncio
    async def test_store_plan_makes_retrievable(self, db_state_manager: PostgresStateManager) -> None:
        plan = self._make_plan()
        await db_state_manager.store_plan('test-project', plan)
        retrieved_plan = await db_state_manager.get_plan('test-project')

        assert retrieved_plan == plan
        assert retrieved_plan.plan_name == 'test-project'
        assert 'Vision' in retrieved_plan.executive_summary

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
        plan = self._make_plan()
        await db_state_manager.store_plan('test-project', plan)
        result = await db_state_manager.delete_plan('test-project')
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_plan_removes_plan(self, db_state_manager: PostgresStateManager) -> None:
        plan = self._make_plan()
        await db_state_manager.store_plan('test-project', plan)
        await db_state_manager.delete_plan('test-project')

        with pytest.raises(PlanNotFoundError):
            await db_state_manager.get_plan('test-project')

    @pytest.mark.asyncio
    async def test_delete_plan_raises_error_when_not_found(self, db_state_manager: PostgresStateManager) -> None:
        with pytest.raises(PlanNotFoundError) as exc_info:
            await db_state_manager.delete_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)


class TestDatabaseDeletePlanCascade:
    @staticmethod
    def _make_plan(name: str = 'Test Plan') -> Plan:
        return Plan(
            plan_name=name,
            executive_summary='### Vision\nVision',
            business_objectives='### Primary Objectives\nObjectives',
            plan_scope='### Included Features\nFeatures',
            stakeholders='### Plan Sponsor\nSponsor',
            architecture_direction='### Architecture Overview\nArch',
            technology_decisions='### Chosen Technologies\nTech',
            plan_structure='### Work Breakdown\nBreakdown',
            resource_requirements='### Team Structure\nTeam',
            risk_management='### Identified Risks\nRisks',
            quality_assurance='### Quality Bar\nStandards',
        )

    @staticmethod
    def _make_phase(name: str = 'phase-1') -> Phase:
        return Phase(
            phase_name=name,
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test dependencies',
            deliverables='Test deliverables',
            phase_status=PhaseStatus.DRAFT,
        )

    @staticmethod
    def _make_roadmap() -> Roadmap:
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

    @staticmethod
    def _make_task(name: str, phase_path: str) -> Task:
        return Task(name=name, phase_path=phase_path)

    @pytest.mark.asyncio
    async def test_delete_plan_removes_roadmap(self, db_state_manager: PostgresStateManager) -> None:
        await db_state_manager.store_plan('my-plan', self._make_plan())
        await db_state_manager.store_roadmap('my-plan', self._make_roadmap())

        await db_state_manager.delete_plan('my-plan')

        with pytest.raises(RoadmapNotFoundError):
            await db_state_manager.get_roadmap('my-plan')

    @pytest.mark.asyncio
    async def test_delete_plan_removes_phases(self, db_state_manager: PostgresStateManager) -> None:
        await db_state_manager.store_plan('my-plan', self._make_plan())
        await db_state_manager.store_phase('my-plan', self._make_phase('phase-1'))
        await db_state_manager.store_phase('my-plan', self._make_phase('phase-2'))

        await db_state_manager.delete_plan('my-plan')

        assert await db_state_manager.list_phases('my-plan') == []

    @pytest.mark.asyncio
    async def test_delete_plan_removes_tasks(self, db_state_manager: PostgresStateManager) -> None:
        await db_state_manager.store_plan('my-plan', self._make_plan())
        await db_state_manager.store_phase('my-plan', self._make_phase('phase-1'))
        task = self._make_task('task-1', 'my-plan/phase-1')
        await db_state_manager.store_task('my-plan/phase-1', task)

        await db_state_manager.delete_plan('my-plan')

        assert await db_state_manager.list_tasks('my-plan/phase-1') == []

    @pytest.mark.asyncio
    async def test_delete_plan_removes_loops(self, db_state_manager: PostgresStateManager) -> None:
        await db_state_manager.store_plan('my-plan', self._make_plan())
        loop = LoopState(loop_type=LoopType.PLAN)
        await db_state_manager.add_loop(loop, 'my-plan')

        await db_state_manager.delete_plan('my-plan')

        with pytest.raises(Exception):
            await db_state_manager.get_loop(loop.id)

    @pytest.mark.asyncio
    async def test_delete_plan_removes_review_sections(self, db_state_manager: PostgresStateManager) -> None:
        await db_state_manager.store_plan('my-plan', self._make_plan())
        await db_state_manager.store_review_section('my-plan/phase-1/review-quality', 'content')
        await db_state_manager.store_review_section('my-plan/phase-1/review-spec', 'content')

        await db_state_manager.delete_plan('my-plan')

        assert await db_state_manager.list_review_sections('my-plan/phase-1') == []

    @pytest.mark.asyncio
    async def test_delete_plan_preserves_other_plans(self, db_state_manager: PostgresStateManager) -> None:
        await db_state_manager.store_plan('plan-a', self._make_plan('Plan A'))
        await db_state_manager.store_plan('plan-b', self._make_plan('Plan B'))
        await db_state_manager.store_roadmap('plan-a', self._make_roadmap())
        await db_state_manager.store_roadmap('plan-b', self._make_roadmap())
        await db_state_manager.store_phase('plan-a', self._make_phase('phase-1'))
        await db_state_manager.store_phase('plan-b', self._make_phase('phase-1'))

        await db_state_manager.delete_plan('plan-a')

        retrieved_plan = await db_state_manager.get_plan('plan-b')
        assert retrieved_plan.plan_name == 'Plan B'
        await db_state_manager.get_roadmap('plan-b')
        assert await db_state_manager.list_phases('plan-b') == ['phase-1']
