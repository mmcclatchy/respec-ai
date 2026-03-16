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
            'phase-critic',
            'task-critic',
            'code-reviewer',
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'frontend-reviewer',
            'backend-api-reviewer',
            'database-reviewer',
            'infrastructure-reviewer',
            'coding-standards-reviewer',
            'review-consolidator',
        }

        actual_agents = {agent.value for agent in CriticAgent}

        assert actual_agents == expected_agents
        assert len(CriticAgent) == 14

    def test_critic_agent_enum_values_use_kebab_case(self) -> None:
        for agent in CriticAgent:
            assert (
                agent.value.endswith('-critic')
                or agent.value.endswith('-reviewer')
                or agent.value.endswith('-checker')
                or agent.value.endswith('-consolidator')
            )
            assert '_' not in agent.value

    def test_from_header_resolves_exact_hyphenated_names(self) -> None:
        for agent in CriticAgent:
            assert CriticAgent.from_header(agent.value.upper()) == agent

    def test_from_header_normalizes_underscores_to_hyphens(self) -> None:
        assert CriticAgent.from_header('TASK_CRITIC') == CriticAgent.TASK_CRITIC
        assert CriticAgent.from_header('CODING_STANDARDS_REVIEWER') == CriticAgent.CODING_STANDARDS_REVIEWER
        assert CriticAgent.from_header('AUTOMATED_QUALITY_CHECKER') == CriticAgent.AUTOMATED_QUALITY_CHECKER

    def test_from_header_resolves_short_aliases(self) -> None:
        assert CriticAgent.from_header('ANALYST') == CriticAgent.ANALYST_CRITIC
        assert CriticAgent.from_header('PLAN') == CriticAgent.PLAN_CRITIC
        assert CriticAgent.from_header('BUILD') == CriticAgent.TASK_CRITIC
        assert CriticAgent.from_header('FRONTEND') == CriticAgent.FRONTEND_REVIEWER
        assert CriticAgent.from_header('CONSOLIDATOR') == CriticAgent.REVIEW_CONSOLIDATOR

    def test_from_header_defaults_to_analyst_critic(self) -> None:
        assert CriticAgent.from_header('UNKNOWN') == CriticAgent.ANALYST_CRITIC
        assert CriticAgent.from_header('NONEXISTENT') == CriticAgent.ANALYST_CRITIC
