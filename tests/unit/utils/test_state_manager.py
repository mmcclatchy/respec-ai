from datetime import datetime

import pytest

from services.models.enums import ProjectStatus, RoadmapStatus, SpecStatus
from services.models.project_plan import ProjectPlan
from services.models.roadmap import Roadmap
from services.models.spec import TechnicalSpec
from services.utils.enums import LoopType
from services.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    ProjectPlanNotFoundError,
    RoadmapNotFoundError,
    SpecNotFoundError,
)
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


class TestProjectPlanOperations(TestInMemoryStateManager):
    def test_store_project_plan_returns_project_name(self, state_manager: InMemoryStateManager) -> None:
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

        result = state_manager.store_project_plan(project_name, project_plan)

        assert result == project_name

    def test_store_project_plan_makes_retrievable(self, state_manager: InMemoryStateManager) -> None:
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

        state_manager.store_project_plan(project_name, project_plan)
        retrieved_plan = state_manager.get_project_plan(project_name)

        assert retrieved_plan == project_plan
        assert retrieved_plan.project_name == project_name
        assert retrieved_plan.project_vision == 'Test vision'

    def test_get_project_plan_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(ProjectPlanNotFoundError) as exc_info:
            state_manager.get_project_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)

    def test_store_project_plan_overwrites_existing(self, state_manager: InMemoryStateManager) -> None:
        project_name = 'same-project'
        original_plan = ProjectPlan(
            project_name='Original Plan',
            project_vision='Original vision',
            project_mission='Original mission',
            project_timeline='Q1 2024',
            project_budget='$100K',
            primary_objectives='Original objectives',
            success_metrics='Original metrics',
            key_performance_indicators='Original KPIs',
            included_features='Feature A',
            excluded_features='Feature B',
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
        updated_plan = ProjectPlan(
            project_name='Updated Plan',
            project_vision='Updated vision',
            project_mission='Updated mission',
            project_timeline='Q2 2024',
            project_budget='$200K',
            primary_objectives='Updated objectives',
            success_metrics='Updated metrics',
            key_performance_indicators='Updated KPIs',
            included_features='Feature C',
            excluded_features='Feature D',
            project_assumptions='Updated assumptions',
            project_constraints='Updated constraints',
            project_sponsor='Updated sponsor',
            key_stakeholders='Updated stakeholders',
            end_users='Updated users',
            work_breakdown='Updated breakdown',
            phases_overview='Updated overview',
            project_dependencies='Updated dependencies',
            team_structure='Updated team',
            technology_requirements='Updated tech',
            infrastructure_needs='Updated infrastructure',
            identified_risks='Updated risks',
            mitigation_strategies='Updated strategies',
            contingency_plans='Updated plans',
            quality_standards='Updated standards',
            testing_strategy='Updated testing',
            acceptance_criteria='Updated criteria',
            reporting_structure='Updated reporting',
            meeting_schedule='Updated meetings',
            documentation_standards='Updated docs',
            project_status=ProjectStatus.ACTIVE,
        )

        state_manager.store_project_plan(project_name, original_plan)
        state_manager.store_project_plan(project_name, updated_plan)
        retrieved_plan = state_manager.get_project_plan(project_name)

        assert retrieved_plan == updated_plan
        assert retrieved_plan.project_name == 'Updated Plan'
        assert retrieved_plan.project_vision == 'Updated vision'
        assert retrieved_plan.project_status == ProjectStatus.ACTIVE

    def test_list_project_plans_returns_empty_for_no_plans(self, state_manager: InMemoryStateManager) -> None:
        result = state_manager.list_project_plans()

        assert result == []

    def test_list_project_plans_returns_all_plan_names(self, state_manager: InMemoryStateManager) -> None:
        plan1 = ProjectPlan(
            project_name='Plan 1',
            project_vision='Vision 1',
            project_mission='Mission 1',
            project_timeline='Q1 2024',
            project_budget='$100K',
            primary_objectives='Objectives 1',
            success_metrics='Metrics 1',
            key_performance_indicators='KPIs 1',
            included_features='Features 1',
            excluded_features='Excluded 1',
            project_assumptions='Assumptions 1',
            project_constraints='Constraints 1',
            project_sponsor='Sponsor 1',
            key_stakeholders='Stakeholders 1',
            end_users='Users 1',
            work_breakdown='Breakdown 1',
            phases_overview='Overview 1',
            project_dependencies='Dependencies 1',
            team_structure='Team 1',
            technology_requirements='Tech 1',
            infrastructure_needs='Infrastructure 1',
            identified_risks='Risks 1',
            mitigation_strategies='Strategies 1',
            contingency_plans='Plans 1',
            quality_standards='Standards 1',
            testing_strategy='Testing 1',
            acceptance_criteria='Criteria 1',
            reporting_structure='Reporting 1',
            meeting_schedule='Meetings 1',
            documentation_standards='Docs 1',
            project_status=ProjectStatus.DRAFT,
        )
        plan2 = ProjectPlan(
            project_name='Plan 2',
            project_vision='Vision 2',
            project_mission='Mission 2',
            project_timeline='Q2 2024',
            project_budget='$200K',
            primary_objectives='Objectives 2',
            success_metrics='Metrics 2',
            key_performance_indicators='KPIs 2',
            included_features='Features 2',
            excluded_features='Excluded 2',
            project_assumptions='Assumptions 2',
            project_constraints='Constraints 2',
            project_sponsor='Sponsor 2',
            key_stakeholders='Stakeholders 2',
            end_users='Users 2',
            work_breakdown='Breakdown 2',
            phases_overview='Overview 2',
            project_dependencies='Dependencies 2',
            team_structure='Team 2',
            technology_requirements='Tech 2',
            infrastructure_needs='Infrastructure 2',
            identified_risks='Risks 2',
            mitigation_strategies='Strategies 2',
            contingency_plans='Plans 2',
            quality_standards='Standards 2',
            testing_strategy='Testing 2',
            acceptance_criteria='Criteria 2',
            reporting_structure='Reporting 2',
            meeting_schedule='Meetings 2',
            documentation_standards='Docs 2',
            project_status=ProjectStatus.ACTIVE,
        )

        state_manager.store_project_plan('project-1', plan1)
        state_manager.store_project_plan('project-2', plan2)
        result = state_manager.list_project_plans()

        assert len(result) == 2
        assert 'project-1' in result
        assert 'project-2' in result

    def test_delete_project_plan_returns_true_when_plan_exists(self, state_manager: InMemoryStateManager) -> None:
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

        state_manager.store_project_plan(project_name, project_plan)
        result = state_manager.delete_project_plan(project_name)

        assert result is True

    def test_delete_project_plan_removes_plan(self, state_manager: InMemoryStateManager) -> None:
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

        state_manager.store_project_plan(project_name, project_plan)
        state_manager.delete_project_plan(project_name)

        with pytest.raises(ProjectPlanNotFoundError):
            state_manager.get_project_plan(project_name)

    def test_delete_project_plan_raises_error_when_not_found(self, state_manager: InMemoryStateManager) -> None:
        with pytest.raises(ProjectPlanNotFoundError) as exc_info:
            state_manager.delete_project_plan('non-existent-project')

        assert 'non-existent-project' in str(exc_info.value)
        assert 'Project plan not found' in str(exc_info.value)

    @pytest.mark.parametrize(
        'project_names',
        [
            ['proj-1', 'proj-2', 'proj-3'],
            ['simple', 'with-dashes', 'with_underscores'],
            ['A', 'B', 'C', 'D', 'E'],
        ],
    )
    def test_project_plan_operations_with_multiple_plans(
        self, state_manager: InMemoryStateManager, project_names: list[str]
    ) -> None:
        # Store multiple plans
        for i, project_name in enumerate(project_names):
            plan = ProjectPlan(
                project_name=f'Plan {i}',
                project_vision=f'Vision {i}',
                project_mission=f'Mission {i}',
                project_timeline='Q1 2024',
                project_budget='$100K',
                primary_objectives=f'Objectives {i}',
                success_metrics=f'Metrics {i}',
                key_performance_indicators=f'KPIs {i}',
                included_features=f'Features {i}',
                excluded_features=f'Excluded {i}',
                project_assumptions=f'Assumptions {i}',
                project_constraints=f'Constraints {i}',
                project_sponsor=f'Sponsor {i}',
                key_stakeholders=f'Stakeholders {i}',
                end_users=f'Users {i}',
                work_breakdown=f'Breakdown {i}',
                phases_overview=f'Overview {i}',
                project_dependencies=f'Dependencies {i}',
                team_structure=f'Team {i}',
                technology_requirements=f'Tech {i}',
                infrastructure_needs=f'Infrastructure {i}',
                identified_risks=f'Risks {i}',
                mitigation_strategies=f'Strategies {i}',
                contingency_plans=f'Plans {i}',
                quality_standards=f'Standards {i}',
                testing_strategy=f'Testing {i}',
                acceptance_criteria=f'Criteria {i}',
                reporting_structure=f'Reporting {i}',
                meeting_schedule=f'Meetings {i}',
                documentation_standards=f'Docs {i}',
                project_status=ProjectStatus.DRAFT,
                creation_date='2024-01-01',
                last_updated='2024-01-01',
                version='1.0',
            )
            state_manager.store_project_plan(project_name, plan)

        # Verify all plans are stored
        all_plans = state_manager.list_project_plans()
        assert len(all_plans) == len(project_names)
        for project_name in project_names:
            assert project_name in all_plans

        # Verify each plan can be retrieved
        for i, project_name in enumerate(project_names):
            plan = state_manager.get_project_plan(project_name)
            assert plan.project_name == f'Plan {i}'
            assert plan.project_vision == f'Vision {i}'


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
