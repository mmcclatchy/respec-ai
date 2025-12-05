from src.models.enums import CriticAgent, FSSDCriteria


class TestFSSDCriteria:
    def test_fssd_criteria_has_all_twelve_criteria(self) -> None:
        expected_criteria = {
            'clarity',
            'completeness',
            'consistency',
            'feasibility',
            'testability',
            'maintainability',
            'scalability',
            'security',
            'performance',
            'usability',
            'documentation',
            'integration',
        }

        actual_criteria = {criteria.value for criteria in FSSDCriteria}

        assert actual_criteria == expected_criteria
        assert len(FSSDCriteria) == 12

    def test_fssd_criteria_enum_values_are_lowercase(self) -> None:
        for criteria in FSSDCriteria:
            assert criteria.value.islower()
            assert ' ' not in criteria.value


class TestCriticAgent:
    def test_critic_agent_has_all_workflow_critics(self) -> None:
        expected_agents = {
            'plan-critic',
            'analyst-critic',
            'roadmap-critic',
            'spec-critic',
            'build-critic',
            'build-reviewer',
        }

        actual_agents = {agent.value for agent in CriticAgent}

        assert actual_agents == expected_agents
        assert len(CriticAgent) == 6

    def test_critic_agent_enum_values_use_kebab_case(self) -> None:
        for agent in CriticAgent:
            assert agent.value.endswith('-critic') or agent.value.endswith('-reviewer')
            assert '_' not in agent.value
