from datetime import datetime

import pytest

from services.models.enums import RoadmapStatus, SpecStatus
from services.models.roadmap import Roadmap
from services.models.spec import TechnicalSpec
from services.utils.enums import LoopType
from services.utils.errors import LoopAlreadyExistsError, LoopNotFoundError, RoadmapNotFoundError, SpecNotFoundError
from services.utils.loop_state import LoopState
from services.utils.state_manager import InMemoryStateManager, Queue


# Import feedback module to ensure LoopState model is fully rebuilt with forward references


class TestQueue:
    def test_queue_initialization(self) -> None:
        queue = Queue[str](maxlen=3)

        assert queue.maxlen == 3
        assert len(queue._deque) == 0

    def test_queue_append_within_limit(self) -> None:
        queue = Queue[str](maxlen=3)

        result1 = queue.append('item1')
        result2 = queue.append('item2')
        result3 = queue.append('item3')

        assert result1 is None  # No items dropped yet
        assert result2 is None
        assert result3 is None
        assert len(queue._deque) == 3

    def test_queue_append_beyond_limit_drops_oldest(self) -> None:
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
    def test_queue_drop_behavior_patterns(self, maxlen: int, items: list[str], expected_dropped: list[str]) -> None:
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
    def project_name(self) -> str:
        return 'test-project'

    @pytest.fixture
    def sample_roadmap(self) -> Roadmap:
        return Roadmap(
            project_name='Test Roadmap',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=[],
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
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_count=0,
        )

    @pytest.fixture
    def sample_spec(self) -> TechnicalSpec:
        return TechnicalSpec(
            phase_name='Sample Spec',
            objectives='Test objectives',
            scope='Test scope',
            dependencies='Test dependencies',
            deliverables='Test deliverables',
            spec_status=SpecStatus.DRAFT,
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_owner='Test Owner',
        )

    @pytest.fixture
    def sample_loop(self) -> LoopState:
        return LoopState(loop_type=LoopType.SPEC)


class TestRoadmapOperations(TestInMemoryStateManager):
    def test_store_roadmap_returns_project_name(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'

        result = state_manager.store_roadmap(project_name, sample_roadmap)

        assert result == project_name

    def test_store_roadmap_makes_retrievable(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'

        state_manager.store_roadmap(project_name, sample_roadmap)
        retrieved_roadmap = state_manager.get_roadmap(project_name)

        assert retrieved_roadmap == sample_roadmap
        assert retrieved_roadmap.project_name == 'Test Roadmap'

    def test_get_roadmap_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError) as exc_info:
            state_manager.get_roadmap('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)

    def test_store_roadmap_overwrites_existing(self, state_manager: InMemoryStateManager) -> None:
        project_name = 'same-project'
        original_roadmap = Roadmap(
            project_name='Original',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=[],
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
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_count=0,
        )
        updated_roadmap = Roadmap(
            project_name='Updated',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=[],
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
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_count=0,
        )

        state_manager.store_roadmap(project_name, original_roadmap)
        state_manager.store_roadmap(project_name, updated_roadmap)

        retrieved = state_manager.get_roadmap(project_name)
        assert retrieved.project_name == 'Updated'

    @pytest.mark.parametrize(
        'project_name,roadmap_name',
        [
            ('proj-1', 'Roadmap 1'),
            ('project-with-dashes', 'Complex Project Roadmap'),
            ('123', 'Numeric Project'),
        ],
    )
    def test_roadmap_storage_with_various_ids(
        self, state_manager: InMemoryStateManager, project_name: str, roadmap_name: str
    ) -> None:
        roadmap = Roadmap(
            project_name=roadmap_name,
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=[],
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
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_count=0,
        )

        stored_id = state_manager.store_roadmap(project_name, roadmap)
        retrieved = state_manager.get_roadmap(project_name)

        assert stored_id == project_name
        assert retrieved.project_name == roadmap_name


class TestSpecOperations(TestInMemoryStateManager):
    def test_store_spec_requires_existing_roadmap(
        self, state_manager: InMemoryStateManager, sample_spec: TechnicalSpec
    ) -> None:
        with pytest.raises(RoadmapNotFoundError):
            state_manager.store_spec('non-existent-project', sample_spec)

    def test_store_spec_returns_spec_name(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        state_manager.store_roadmap(project_name, sample_roadmap)

        result = state_manager.store_spec(project_name, sample_spec)

        assert result == sample_spec.phase_name

    def test_store_spec_makes_retrievable(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        state_manager.store_roadmap(project_name, sample_roadmap)

        state_manager.store_spec(project_name, sample_spec)
        retrieved_spec = state_manager.get_spec(project_name, sample_spec.phase_name)

        assert retrieved_spec == sample_spec
        assert retrieved_spec.objectives == 'Test objectives'

    def test_get_spec_raises_error_when_roadmap_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError):
            state_manager.get_spec('non-existent-project', 'any-spec')

    def test_get_spec_raises_error_when_spec_not_found(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'
        state_manager.store_roadmap(project_name, sample_roadmap)

        with pytest.raises(SpecNotFoundError):
            state_manager.get_spec(project_name, 'non-existent-spec')

    def test_list_specs_returns_empty_for_empty_roadmap(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'empty-project'
        state_manager.store_roadmap(project_name, sample_roadmap)

        spec_names = state_manager.list_specs(project_name)

        assert spec_names == []

    def test_list_specs_returns_all_spec_names(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'multi-spec-project'
        state_manager.store_roadmap(project_name, sample_roadmap)

        spec1 = TechnicalSpec(
            phase_name='Spec 1',
            objectives='Obj 1',
            scope='Scope 1',
            dependencies='Dep 1',
            deliverables='Del 1',
            spec_status=SpecStatus.DRAFT,
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_owner='Test Owner',
        )
        spec2 = TechnicalSpec(
            phase_name='Spec 2',
            objectives='Obj 2',
            scope='Scope 2',
            dependencies='Dep 2',
            deliverables='Del 2',
            spec_status=SpecStatus.DRAFT,
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_owner='Test Owner',
        )

        state_manager.store_spec(project_name, spec1)
        state_manager.store_spec(project_name, spec2)

        spec_names = state_manager.list_specs(project_name)

        assert len(spec_names) == 2
        assert 'Spec 1' in spec_names
        assert 'Spec 2' in spec_names

    def test_list_specs_raises_error_when_roadmap_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError):
            state_manager.list_specs('non-existent-project')

    def test_delete_spec_returns_true_when_spec_exists(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        state_manager.store_roadmap(project_name, sample_roadmap)
        state_manager.store_spec(project_name, sample_spec)

        result = state_manager.delete_spec(project_name, sample_spec.phase_name)

        assert result is True

    def test_delete_spec_removes_spec_from_roadmap(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, sample_spec: TechnicalSpec
    ) -> None:
        project_name = 'test-project'
        state_manager.store_roadmap(project_name, sample_roadmap)
        state_manager.store_spec(project_name, sample_spec)

        state_manager.delete_spec(project_name, sample_spec.phase_name)

        # Should raise SpecNotFoundError now
        with pytest.raises(SpecNotFoundError):
            state_manager.get_spec(project_name, sample_spec.phase_name)

    def test_delete_spec_returns_false_when_spec_not_found(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap
    ) -> None:
        project_name = 'test-project'
        state_manager.store_roadmap(project_name, sample_roadmap)

        result = state_manager.delete_spec(project_name, 'non-existent-spec')

        assert result is False

    def test_delete_spec_raises_error_when_roadmap_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(RoadmapNotFoundError):
            state_manager.delete_spec('non-existent-project', 'any-spec')

    @pytest.mark.parametrize(
        'spec_names',
        [
            ['Single Spec'],
            ['First Spec', 'Second Spec'],
            ['Alpha', 'Beta', 'Gamma', 'Delta'],
        ],
    )
    def test_spec_operations_with_multiple_specs(
        self, state_manager: InMemoryStateManager, sample_roadmap: Roadmap, spec_names: list[str]
    ) -> None:
        project_name = 'multi-spec-test'
        state_manager.store_roadmap(project_name, sample_roadmap)

        # Store all specs
        for spec_name in spec_names:
            spec = TechnicalSpec(
                phase_name=spec_name,
                objectives=f'Obj {spec_name}',
                scope=f'Scope {spec_name}',
                dependencies=f'Dep {spec_name}',
                deliverables=f'Del {spec_name}',
                spec_status=SpecStatus.DRAFT,
                creation_date=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                spec_owner='Test Owner',
            )
            state_manager.store_spec(project_name, spec)

        # List should return all names
        listed_names = state_manager.list_specs(project_name)
        assert len(listed_names) == len(spec_names)
        for name in spec_names:
            assert name in listed_names

        # Delete half the specs
        to_delete = spec_names[: len(spec_names) // 2] if len(spec_names) > 1 else []
        for name in to_delete:
            result = state_manager.delete_spec(project_name, name)
            assert result is True

        # List should return remaining specs
        remaining_names = state_manager.list_specs(project_name)
        expected_remaining = [name for name in spec_names if name not in to_delete]
        assert len(remaining_names) == len(expected_remaining)
        for name in expected_remaining:
            assert name in remaining_names


class TestLoopOperations(TestInMemoryStateManager):
    def test_add_loop_stores_loop_state(
        self, state_manager: InMemoryStateManager, project_name: str, sample_loop: LoopState
    ) -> None:
        state_manager.add_loop(sample_loop, project_name)

        retrieved_loop = state_manager.get_loop(sample_loop.id)
        assert retrieved_loop == sample_loop

    def test_add_loop_raises_error_for_duplicate_id(
        self, state_manager: InMemoryStateManager, project_name: str, sample_loop: LoopState
    ) -> None:
        state_manager.add_loop(sample_loop, project_name)

        duplicate_loop = LoopState(loop_type=LoopType.PLAN)
        duplicate_loop.id = sample_loop.id  # Force same ID

        with pytest.raises(LoopAlreadyExistsError):
            state_manager.add_loop(duplicate_loop, project_name)

    def test_get_loop_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(LoopNotFoundError):
            state_manager.get_loop('non-existent-loop-id')

    def test_loop_history_management_respects_max_size(
        self, state_manager: InMemoryStateManager, project_name: str
    ) -> None:
        # State manager initialized with max_history_size=3
        loops = [
            LoopState(loop_type=LoopType.PLAN),
            LoopState(loop_type=LoopType.SPEC),
            LoopState(loop_type=LoopType.BUILD_PLAN),
            LoopState(loop_type=LoopType.BUILD_CODE),  # This should cause first to be dropped
        ]

        for loop in loops:
            state_manager.add_loop(loop, project_name)

        # First loop should have been dropped from active loops
        with pytest.raises(LoopNotFoundError):
            state_manager.get_loop(loops[0].id)

        # Last 3 should still exist
        for loop in loops[1:]:
            retrieved = state_manager.get_loop(loop.id)
            assert retrieved == loop


class TestCrossOperationIntegration(TestInMemoryStateManager):
    def test_multiple_projects_independent_state(self, state_manager: InMemoryStateManager) -> None:
        # Create two projects with different roadmaps and specs
        project1_roadmap = Roadmap(
            project_name='Project 1 Roadmap',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=[],
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
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_count=0,
        )
        project2_roadmap = Roadmap(
            project_name='Project 2 Roadmap',
            project_goal='Test goal',
            total_duration='8 weeks',
            team_size='4 developers',
            roadmap_budget='$100,000',
            specs=[],
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
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_count=0,
        )

        state_manager.store_roadmap('project-1', project1_roadmap)
        state_manager.store_roadmap('project-2', project2_roadmap)

        spec1 = TechnicalSpec(
            phase_name='P1 Spec',
            objectives='P1 Obj',
            scope='P1 Scope',
            dependencies='P1 Dep',
            deliverables='P1 Del',
            spec_status=SpecStatus.DRAFT,
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_owner='Test Owner',
        )
        spec2 = TechnicalSpec(
            phase_name='P2 Spec',
            objectives='P2 Obj',
            scope='P2 Scope',
            dependencies='P2 Dep',
            deliverables='P2 Del',
            spec_status=SpecStatus.DRAFT,
            creation_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            spec_owner='Test Owner',
        )

        state_manager.store_spec('project-1', spec1)
        state_manager.store_spec('project-2', spec2)

        # Each project should only see its own specs
        p1_specs = state_manager.list_specs('project-1')
        p2_specs = state_manager.list_specs('project-2')

        assert 'P1 Spec' in p1_specs
        assert 'P1 Spec' not in p2_specs
        assert 'P2 Spec' in p2_specs
        assert 'P2 Spec' not in p1_specs

    def test_loops_and_roadmaps_coexist_independently(
        self, state_manager: InMemoryStateManager, project_name: str, sample_roadmap: Roadmap, sample_loop: LoopState
    ) -> None:
        # Add both loop and roadmap data
        state_manager.add_loop(sample_loop, project_name)
        state_manager.store_roadmap('test-project', sample_roadmap)

        # Both should be retrievable independently
        retrieved_loop = state_manager.get_loop(sample_loop.id)
        retrieved_roadmap = state_manager.get_roadmap('test-project')

        assert retrieved_loop == sample_loop
        assert retrieved_roadmap == sample_roadmap

    def test_state_manager_initialization_parameters(self, project_name: str) -> None:
        # Test with custom max_history_size
        custom_state_manager = InMemoryStateManager(max_history_size=5)

        # Should be able to store more loops before dropping
        loops = [LoopState(loop_type=LoopType.PLAN) for _ in range(6)]

        for loop in loops:
            custom_state_manager.add_loop(loop, project_name)

        # First loop should be dropped (6 > 5)
        with pytest.raises(LoopNotFoundError):
            custom_state_manager.get_loop(loops[0].id)

        # Last 5 should exist
        for loop in loops[1:]:
            retrieved = custom_state_manager.get_loop(loop.id)
            assert retrieved == loop
