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
from src.utils.state_manager import InMemoryStateManager, Queue


# Import feedback module to ensure LoopState model is fully rebuilt with forward references


class TestQueue:
    def test_queue_initialization(self) -> None:
        queue = Queue[str](maxlen=3)

        assert queue.maxlen == 3
        assert len(queue._deque) == 0

    @pytest.mark.asyncio
    async def test_queue_append_within_limit(self) -> None:
        queue = Queue[str](maxlen=3)

        result1 = queue.append('item1')
        result2 = queue.append('item2')
        result3 = queue.append('item3')

        assert result1 is None  # No items dropped yet
        assert result2 is None
        assert result3 is None
        assert len(queue._deque) == 3

    @pytest.mark.asyncio
    async def test_queue_append_beyond_limit_drops_oldest(self) -> None:
        queue = Queue[str](maxlen=2)

        queue.append('first')
        queue.append('second')
        dropped = queue.append('third')

        assert dropped == 'first'
        assert len(queue._deque) == 2
        assert 'second' in queue._deque
        assert 'third' in queue._deque

    @pytest.mark.parametrize(
        'maxlen,items,expected_dropped',
        [
            (1, ['a', 'b', 'c'], ['a', 'b']),
            (3, ['1', '2', '3', '4', '5'], ['1', '2']),
            (5, ['x', 'y'], []),
        ],
    )
    @pytest.mark.asyncio
    async def test_queue_drop_behavior_patterns(
        self, maxlen: int, items: list[str], expected_dropped: list[str]
    ) -> None:
        queue = Queue[str](maxlen=maxlen)
        dropped_items = []

        for item in items:
            result = queue.append(item)
            if result is not None:
                dropped_items.append(result)

        assert dropped_items == expected_dropped


class TestInMemoryStateManager:
    @pytest.fixture
    def state_manager(self) -> InMemoryStateManager:
        return InMemoryStateManager(max_history_size=3)

    @pytest.fixture
    def plan_name(self) -> str:
        return 'test-project'

    @pytest.fixture
    def sample_roadmap(self) -> Roadmap:
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
    def sample_phase(self) -> Phase:
        return Phase(
            phase_name='Sample Phase',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test dependencies',
            deliverables='Test deliverables',
            phase_status=PhaseStatus.DRAFT,
        )

    @pytest.fixture
    def sample_loop(self) -> LoopState:
        return LoopState(loop_type=LoopType.PHASE)


class TestRoadmapOperations(TestInMemoryStateManager):
    @pytest.mark.asyncio
    async def test_store_roadmap_returns_plan_name(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'

        result = await state_manager.store_roadmap(plan_name, sample_roadmap)

        assert result == plan_name

    @pytest.mark.asyncio
    async def test_store_roadmap_makes_retrievable(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'

        await state_manager.store_roadmap(plan_name, sample_roadmap)
        retrieved_roadmap = await state_manager.get_roadmap(plan_name)

        assert retrieved_roadmap == sample_roadmap
        assert retrieved_roadmap.plan_name == 'Test Roadmap'

    @pytest.mark.asyncio
    async def test_get_roadmap_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError) as exc_info:
            await state_manager.get_roadmap('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_roadmap_overwrites_existing(self, state_manager: InMemoryStateManager) -> None:
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

        await state_manager.store_roadmap(plan_name, original_roadmap)
        await state_manager.store_roadmap(plan_name, updated_roadmap)

        retrieved = await state_manager.get_roadmap(plan_name)
        assert retrieved.plan_name == 'Updated'

    @pytest.mark.parametrize(
        'plan_name,roadmap_name',
        [
            ('proj-1', 'Roadmap 1'),
            ('project-with-dashes', 'Complex Plan Roadmap'),
            ('123', 'Numeric Plan'),
        ],
    )
    @pytest.mark.asyncio
    async def test_roadmap_storage_with_various_ids(
        self, state_manager: InMemoryStateManager, plan_name: str, roadmap_name: str
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

        stored_id = await state_manager.store_roadmap(plan_name, roadmap)
        retrieved = await state_manager.get_roadmap(plan_name)

        assert stored_id == plan_name
        assert retrieved.plan_name == roadmap_name


class TestPhaseOperations(TestInMemoryStateManager):
    @pytest.mark.asyncio
    async def test_store_phase_initializes_project_storage(
        self, state_manager: InMemoryStateManager, sample_phase: Phase
    ) -> None:
        result = await state_manager.store_phase('new-project', sample_phase)
        assert result == sample_phase.phase_name

        # Verify phase was stored
        retrieved = await state_manager.get_phase('new-project', sample_phase.phase_name)
        assert retrieved.phase_name == sample_phase.phase_name

    @pytest.mark.asyncio
    async def test_store_phase_returns_phase_name(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

        result = await state_manager.store_phase(plan_name, sample_phase)

        assert result == sample_phase.phase_name

    @pytest.mark.asyncio
    async def test_store_phase_makes_retrievable(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

        await state_manager.store_phase(plan_name, sample_phase)
        retrieved_phase = await state_manager.get_phase(plan_name, sample_phase.phase_name)

        assert retrieved_phase == sample_phase
        assert retrieved_phase.objectives == 'Test objectives'

    @pytest.mark.asyncio
    async def test_get_phase_raises_error_when_phase_not_found_in_project(
        self, state_manager: InMemoryStateManager, sample_phase: Phase
    ) -> None:
        # Store a phase first
        await state_manager.store_phase('test-project', sample_phase)

        # Try to get non-existent phase
        with pytest.raises(PhaseNotFoundError, match='Phase not found'):
            await state_manager.get_phase('test-project', 'nonexistent-phase')

    @pytest.mark.asyncio
    async def test_get_phase_raises_error_when_phase_not_found(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

        with pytest.raises(PhaseNotFoundError):
            await state_manager.get_phase(plan_name, 'non-existent-phase')

    @pytest.mark.asyncio
    async def test_list_phases_returns_empty_for_empty_roadmap(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'empty-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

        phase_names = await state_manager.list_phases(plan_name)

        assert phase_names == []

    @pytest.mark.asyncio
    async def test_list_phases_returns_all_phase_names(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'multi-phase-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

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

        await state_manager.store_phase(plan_name, phase1)
        await state_manager.store_phase(plan_name, phase2)

        phase_names = await state_manager.list_phases(plan_name)

        assert len(phase_names) == 2
        assert 'phase-1' in phase_names
        assert 'phase-2' in phase_names

    @pytest.mark.asyncio
    async def test_list_phases_returns_empty_for_project_without_phases(
        self, state_manager: InMemoryStateManager
    ) -> None:
        result = await state_manager.list_phases('project-without-phases')
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_phase_returns_true_when_phase_exists(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)
        await state_manager.store_phase(plan_name, sample_phase)

        result = await state_manager.delete_phase(plan_name, sample_phase.phase_name)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_phase_removes_phase_from_roadmap(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)
        await state_manager.store_phase(plan_name, sample_phase)

        await state_manager.delete_phase(plan_name, sample_phase.phase_name)

        # Should raise PhaseNotFoundError now
        with pytest.raises(PhaseNotFoundError):
            await state_manager.get_phase(plan_name, sample_phase.phase_name)

    @pytest.mark.asyncio
    async def test_delete_phase_returns_false_when_phase_not_found(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

        result = await state_manager.delete_phase(plan_name, 'non-existent-phase')

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_phase_returns_false_for_nonexistent_project(
        self, state_manager: InMemoryStateManager
    ) -> None:
        result = await state_manager.delete_phase('nonexistent-project', 'nonexistent-phase')
        assert result is False

    @pytest.mark.parametrize(
        'phase_names',
        [
            ['single-phase'],
            ['first-phase', 'second-phase'],
            ['alpha', 'beta', 'gamma', 'delta'],
        ],
    )
    @pytest.mark.asyncio
    async def test_phase_operations_with_multiple_phases(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, phase_names: list[str]
    ) -> None:
        plan_name = 'multi-phase-test'
        await state_manager.store_roadmap(plan_name, sample_roadmap)

        # Store all phases
        for phase_name in phase_names:
            phase = Phase(
                phase_name=phase_name,
                objectives=f'Obj {phase_name}',
                scope=f'Scope {phase_name}',
                dependencies=f'Dep {phase_name}',
                deliverables=f'Del {phase_name}',
                phase_status=PhaseStatus.DRAFT,
            )
            await state_manager.store_phase(plan_name, phase)

        # List should return all names
        listed_names = await state_manager.list_phases(plan_name)
        assert len(listed_names) == len(phase_names)
        for name in phase_names:
            assert name in listed_names

        # Delete half the phases
        to_delete = phase_names[: len(phase_names) // 2] if len(phase_names) > 1 else []
        for name in to_delete:
            result = await state_manager.delete_phase(plan_name, name)
            assert result is True

        # List should return remaining phases
        remaining_names = await state_manager.list_phases(plan_name)
        expected_remaining = [name for name in phase_names if name not in to_delete]
        assert len(remaining_names) == len(expected_remaining)
        for name in expected_remaining:
            assert name in remaining_names


class TestUpdatePhaseFrozenFields(TestInMemoryStateManager):
    @pytest.mark.asyncio
    async def test_update_phase_preserves_frozen_fields_with_real_content(
        self, state_manager: InMemoryStateManager, sample_phase: Phase
    ) -> None:
        plan_name = 'test-project'
        await state_manager.store_phase(plan_name, sample_phase)

        updated = Phase(
            phase_name=sample_phase.phase_name,
            objectives='CHANGED objectives',
            scope='CHANGED scope',
            dependencies='CHANGED dependencies',
            deliverables='CHANGED deliverables',
            architecture='New architecture content',
            phase_status=PhaseStatus.DRAFT,
        )
        await state_manager.update_phase(plan_name, sample_phase.phase_name, updated)

        retrieved = await state_manager.get_phase(plan_name, sample_phase.phase_name)
        assert retrieved.objectives == 'Test objectives'
        assert retrieved.scope == 'Test scope'
        assert retrieved.dependencies == 'Test dependencies'
        assert retrieved.deliverables == 'Test deliverables'
        assert retrieved.architecture == 'New architecture content'

    @pytest.mark.asyncio
    async def test_update_phase_allows_populating_placeholder_fields(self, state_manager: InMemoryStateManager) -> None:
        plan_name = 'test-project'
        placeholder_phase = Phase(phase_name='placeholder-phase', phase_status=PhaseStatus.DRAFT)
        await state_manager.store_phase(plan_name, placeholder_phase)

        populated = Phase(
            phase_name='placeholder-phase',
            objectives='Real objectives from architect',
            scope='Real scope from architect',
            dependencies='Real dependencies from architect',
            deliverables='Real deliverables from architect',
            architecture='Architecture content',
            phase_status=PhaseStatus.DRAFT,
        )
        await state_manager.update_phase(plan_name, 'placeholder-phase', populated)

        retrieved = await state_manager.get_phase(plan_name, 'placeholder-phase')
        assert retrieved.objectives == 'Real objectives from architect'
        assert retrieved.scope == 'Real scope from architect'
        assert retrieved.dependencies == 'Real dependencies from architect'
        assert retrieved.deliverables == 'Real deliverables from architect'

    @pytest.mark.asyncio
    async def test_update_phase_handles_mixed_placeholder_and_real_content(
        self, state_manager: InMemoryStateManager
    ) -> None:
        plan_name = 'test-project'
        partial_phase = Phase(
            phase_name='partial-phase',
            objectives='Real objectives from roadmap',
            phase_status=PhaseStatus.DRAFT,
        )
        await state_manager.store_phase(plan_name, partial_phase)

        updated = Phase(
            phase_name='partial-phase',
            objectives='CHANGED objectives',
            scope='Real scope from architect',
            dependencies='Real dependencies from architect',
            deliverables='Real deliverables from architect',
            phase_status=PhaseStatus.DRAFT,
        )
        await state_manager.update_phase(plan_name, 'partial-phase', updated)

        retrieved = await state_manager.get_phase(plan_name, 'partial-phase')
        assert retrieved.objectives == 'Real objectives from roadmap'
        assert retrieved.scope == 'Real scope from architect'
        assert retrieved.dependencies == 'Real dependencies from architect'
        assert retrieved.deliverables == 'Real deliverables from architect'

    @pytest.mark.asyncio
    async def test_update_phase_freezes_newly_populated_fields_on_second_iteration(
        self, state_manager: InMemoryStateManager
    ) -> None:
        plan_name = 'test-project'
        placeholder_phase = Phase(phase_name='evolving-phase', phase_status=PhaseStatus.DRAFT)
        await state_manager.store_phase(plan_name, placeholder_phase)

        first_update = Phase(
            phase_name='evolving-phase',
            objectives='Objectives set in iteration 1',
            scope='Scope set in iteration 1',
            dependencies='Dependencies set in iteration 1',
            deliverables='Deliverables set in iteration 1',
            phase_status=PhaseStatus.DRAFT,
        )
        await state_manager.update_phase(plan_name, 'evolving-phase', first_update)

        second_update = Phase(
            phase_name='evolving-phase',
            objectives='Trying to change in iteration 2',
            scope='Trying to change in iteration 2',
            dependencies='Trying to change in iteration 2',
            deliverables='Trying to change in iteration 2',
            architecture='Refined architecture',
            phase_status=PhaseStatus.DRAFT,
        )
        await state_manager.update_phase(plan_name, 'evolving-phase', second_update)

        retrieved = await state_manager.get_phase(plan_name, 'evolving-phase')
        assert retrieved.objectives == 'Objectives set in iteration 1'
        assert retrieved.scope == 'Scope set in iteration 1'
        assert retrieved.architecture == 'Refined architecture'


class TestLoopOperations(TestInMemoryStateManager):
    @pytest.mark.asyncio
    async def test_add_loop_stores_loop_state(
        self, state_manager: InMemoryStateManager, plan_name: str, sample_loop: LoopState
    ) -> None:
        await state_manager.add_loop(sample_loop, plan_name)

        retrieved_loop = await state_manager.get_loop(sample_loop.id)
        assert retrieved_loop == sample_loop

    @pytest.mark.asyncio
    async def test_add_loop_raises_error_for_duplicate_id(
        self, state_manager: InMemoryStateManager, plan_name: str, sample_loop: LoopState
    ) -> None:
        await state_manager.add_loop(sample_loop, plan_name)

        duplicate_loop = LoopState(loop_type=LoopType.PLAN)
        duplicate_loop.id = sample_loop.id  # Force same ID

        with pytest.raises(LoopAlreadyExistsError):
            await state_manager.add_loop(duplicate_loop, plan_name)

    @pytest.mark.asyncio
    async def test_get_loop_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(LoopNotFoundError):
            await state_manager.get_loop('non-existent-loop-id')

    @pytest.mark.asyncio
    async def test_loop_history_management_respects_max_size(
        self, state_manager: InMemoryStateManager, plan_name: str
    ) -> None:
        # State manager initialized with max_history_size=3
        loops = [
            LoopState(loop_type=LoopType.PLAN),
            LoopState(loop_type=LoopType.PHASE),
            LoopState(loop_type=LoopType.TASK),
            LoopState(loop_type=LoopType.ANALYST),  # This should cause first to be dropped
        ]

        for loop in loops:
            await state_manager.add_loop(loop, plan_name)

        # First loop should have been dropped from active loops
        with pytest.raises(LoopNotFoundError):
            await state_manager.get_loop(loops[0].id)

        # Last 3 should still exist
        for loop in loops[1:]:
            retrieved = await state_manager.get_loop(loop.id)
            assert retrieved == loop


class TestPlanOperations(TestInMemoryStateManager):
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
    async def test_store_plan_returns_plan_name(self, state_manager: InMemoryStateManager) -> None:
        plan = self._make_plan()
        result = await state_manager.store_plan('test-project', plan)
        assert result == 'test-project'

    @pytest.mark.asyncio
    async def test_store_plan_makes_retrievable(self, state_manager: InMemoryStateManager) -> None:
        plan = self._make_plan()
        await state_manager.store_plan('test-project', plan)
        retrieved_plan = await state_manager.get_plan('test-project')

        assert retrieved_plan == plan
        assert retrieved_plan.plan_name == 'test-project'
        assert 'Vision' in retrieved_plan.executive_summary

    @pytest.mark.asyncio
    async def test_get_plan_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(PlanNotFoundError) as exc_info:
            await state_manager.get_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_plan_overwrites_existing(self, state_manager: InMemoryStateManager) -> None:
        original = self._make_plan(name='Original Plan')
        updated = self._make_plan(name='Updated Plan', suffix=' updated', status=PlanStatus.ACTIVE)

        await state_manager.store_plan('same-project', original)
        await state_manager.store_plan('same-project', updated)
        retrieved_plan = await state_manager.get_plan('same-project')

        assert retrieved_plan == updated
        assert retrieved_plan.plan_name == 'Updated Plan'
        assert 'Vision updated' in retrieved_plan.executive_summary
        assert retrieved_plan.plan_status == PlanStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_list_plans_returns_empty_for_no_plans(self, state_manager: InMemoryStateManager) -> None:
        result = await state_manager.list_plans()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_plans_returns_all_plan_names(self, state_manager: InMemoryStateManager) -> None:
        plan1 = self._make_plan(name='Plan 1', suffix=' 1')
        plan2 = self._make_plan(name='Plan 2', suffix=' 2', status=PlanStatus.ACTIVE)

        await state_manager.store_plan('project-1', plan1)
        await state_manager.store_plan('project-2', plan2)
        result = await state_manager.list_plans()

        assert len(result) == 2
        assert 'project-1' in result
        assert 'project-2' in result

    @pytest.mark.asyncio
    async def test_delete_plan_returns_true_when_plan_exists(self, state_manager: InMemoryStateManager) -> None:
        plan = self._make_plan()
        await state_manager.store_plan('test-project', plan)
        result = await state_manager.delete_plan('test-project')
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_plan_removes_plan(self, state_manager: InMemoryStateManager) -> None:
        plan = self._make_plan()
        await state_manager.store_plan('test-project', plan)
        await state_manager.delete_plan('test-project')

        with pytest.raises(PlanNotFoundError):
            await state_manager.get_plan('test-project')

    @pytest.mark.asyncio
    async def test_delete_plan_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(PlanNotFoundError) as exc_info:
            await state_manager.delete_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)

    @pytest.mark.parametrize(
        'plan_names',
        [
            ['proj-1', 'proj-2', 'proj-3'],
            ['simple', 'with-dashes', 'with_underscores'],
            ['A', 'B', 'C', 'D', 'E'],
        ],
    )
    @pytest.mark.asyncio
    async def test_plan_operations_with_multiple_plans(
        self, state_manager: InMemoryStateManager, plan_names: list[str]
    ) -> None:
        for i, plan_name in enumerate(plan_names):
            plan = self._make_plan(name=f'Plan {i}', suffix=f' {i}')
            await state_manager.store_plan(plan_name, plan)

        all_plans = await state_manager.list_plans()
        assert len(all_plans) == len(plan_names)
        for plan_name in plan_names:
            assert plan_name in all_plans

        for i, plan_name in enumerate(plan_names):
            plan = await state_manager.get_plan(plan_name)
            assert plan.plan_name == f'Plan {i}'
            assert f'Vision {i}' in plan.executive_summary


class TestCrossOperationIntegration(TestInMemoryStateManager):
    @pytest.mark.asyncio
    async def test_multiple_projects_independent_state(self, state_manager: InMemoryStateManager) -> None:
        # Create two projects with different roadmaps and phases
        project1_roadmap = Roadmap(
            plan_name='Project 1 Roadmap',
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
        project2_roadmap = Roadmap(
            plan_name='Project 2 Roadmap',
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

        await state_manager.store_roadmap('project-1', project1_roadmap)
        await state_manager.store_roadmap('project-2', project2_roadmap)

        phase1 = Phase(
            phase_name='p1-phase',
            objectives='P1 Obj',
            scope='P1 Scope',
            dependencies='P1 Dep',
            deliverables='P1 Del',
            phase_status=PhaseStatus.DRAFT,
        )
        phase2 = Phase(
            phase_name='p2-phase',
            objectives='P2 Obj',
            scope='P2 Scope',
            dependencies='P2 Dep',
            deliverables='P2 Del',
            phase_status=PhaseStatus.DRAFT,
        )

        await state_manager.store_phase('project-1', phase1)
        await state_manager.store_phase('project-2', phase2)

        # Each project should only see its own phases
        p1_phases = await state_manager.list_phases('project-1')
        p2_phases = await state_manager.list_phases('project-2')

        assert 'p1-phase' in p1_phases
        assert 'p1-phase' not in p2_phases
        assert 'p2-phase' in p2_phases
        assert 'p2-phase' not in p1_phases

    @pytest.mark.asyncio
    async def test_loops_and_roadmaps_coexist_independently(
        self, state_manager: InMemoryStateManager, plan_name: str, sample_roadmap: Roadmap, sample_loop: LoopState
    ) -> None:
        # Add both loop and roadmap data
        await state_manager.add_loop(sample_loop, plan_name)
        await state_manager.store_roadmap('test-project', sample_roadmap)

        # Both should be retrievable independently
        retrieved_loop = await state_manager.get_loop(sample_loop.id)
        retrieved_roadmap = await state_manager.get_roadmap('test-project')

        assert retrieved_loop == sample_loop
        assert retrieved_roadmap == sample_roadmap

    @pytest.mark.asyncio
    async def test_state_manager_initialization_parameters(self, plan_name: str) -> None:
        # Test with custom max_history_size
        custom_state_manager = InMemoryStateManager(max_history_size=5)

        # Should be able to store more loops before dropping
        loops = [LoopState(loop_type=LoopType.PLAN) for _ in range(6)]

        for loop in loops:
            await custom_state_manager.add_loop(loop, plan_name)

        # First loop should be dropped (6 > 5)
        with pytest.raises(LoopNotFoundError):
            await custom_state_manager.get_loop(loops[0].id)

        # Last 5 should exist
        for loop in loops[1:]:
            retrieved = await custom_state_manager.get_loop(loop.id)
            assert retrieved == loop


class TestReviewSectionManagement(TestInMemoryStateManager):
    @pytest.mark.asyncio
    async def test_store_and_get_review_section(self, state_manager: InMemoryStateManager) -> None:
        key = 'my-plan/phase-1/review-quality-check'
        content = '### Automated Quality Check (Score: 65/70)\n\nAll tests pass.'

        result = await state_manager.store_review_section(key, content)
        assert 'Stored review section' in result

        retrieved = await state_manager.get_review_section(key)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_get_review_section_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(ValueError, match='Review section not found'):
            await state_manager.get_review_section('nonexistent/key')

    @pytest.mark.asyncio
    async def test_list_review_sections_filters_by_parent_key(self, state_manager: InMemoryStateManager) -> None:
        await state_manager.store_review_section('plan/phase-1/review-quality-check', 'content1')
        await state_manager.store_review_section('plan/phase-1/review-spec-alignment', 'content2')
        await state_manager.store_review_section('plan/phase-2/review-quality-check', 'content3')

        keys = await state_manager.list_review_sections('plan/phase-1')
        assert keys == [
            'plan/phase-1/review-quality-check',
            'plan/phase-1/review-spec-alignment',
        ]

    @pytest.mark.asyncio
    async def test_list_review_sections_empty_result(self, state_manager: InMemoryStateManager) -> None:
        keys = await state_manager.list_review_sections('nonexistent/parent')
        assert keys == []

    @pytest.mark.asyncio
    async def test_store_overwrites_existing(self, state_manager: InMemoryStateManager) -> None:
        key = 'plan/phase-1/review-quality-check'
        await state_manager.store_review_section(key, 'old content')
        await state_manager.store_review_section(key, 'new content')

        retrieved = await state_manager.get_review_section(key)
        assert retrieved == 'new content'
