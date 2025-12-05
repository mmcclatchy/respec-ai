#!/usr/bin/env python3
"""
Generate markdown templates from Pydantic models.

This script generates example markdown templates by creating sample instances
of each model and outputting their markdown representation. This ensures
templates stay synchronized with model definitions.
"""

from src.models.build_plan import BuildPlan
from src.models.enums import BuildStatus, CriticAgent, ProjectStatus, RequirementsStatus, RoadmapStatus
from src.models.feature_requirements import FeatureRequirements
from src.models.feedback import CriticFeedback
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap


def generate_roadmap_template() -> str:
    roadmap = Roadmap(
        project_name='[Project Name]',
        project_goal='[Brief description of the main project goal]',
        total_duration="[Expected duration, e.g., '6 months']",
        team_size="[Team size, e.g., '5 developers']",
        roadmap_budget="[Budget, e.g., '$500,000']",
        critical_path_analysis='[Analysis of critical path dependencies]',
        key_risks='[Primary project risks]',
        mitigation_plans='[Risk mitigation strategies]',
        buffer_time="[Buffer time allocation, e.g., '2 weeks']",
        development_resources='[Development resources needed]',
        infrastructure_requirements='[Infrastructure requirements]',
        external_dependencies='[External dependencies]',
        quality_assurance_plan='[QA plan overview]',
        technical_milestones='[Key technical milestones]',
        business_milestones='[Key business milestones]',
        quality_gates='[Quality gates and checkpoints]',
        performance_targets='[Performance targets and metrics]',
        roadmap_status=RoadmapStatus.DRAFT,
    )
    return roadmap.build_markdown()


def generate_build_plan_template() -> str:
    build_plan = BuildPlan(
        project_name='[Project Name]',
        project_goal='[Main project goal and objectives]',
        total_duration='[Expected build duration]',
        team_size='[Development team size]',
        primary_language='[Primary programming language]',
        framework='[Main framework or technology stack]',
        database='[Database technology]',
        development_environment='[Development environment setup]',
        database_schema='[Database schema description]',
        api_architecture='[API architecture approach]',
        frontend_architecture='[Frontend architecture approach]',
        core_features='[Core feature list]',
        integration_points='[Key integration points]',
        testing_strategy='[Testing approach and strategy]',
        code_standards='[Code standards and conventions]',
        performance_requirements='[Performance requirements]',
        security_implementation='[Security implementation approach]',
        build_status=BuildStatus.PLANNING,
    )
    return build_plan.build_markdown()


def generate_feature_requirements_template() -> str:
    requirements = FeatureRequirements(
        project_name='[Feature Name]',
        feature_description='[Detailed feature description]',
        problem_statement='[Problem this feature solves]',
        target_users='[Target user groups]',
        business_value='[Business value and justification]',
        user_stories="[User stories in 'As a... I want... So that...' format]",
        acceptance_criteria='[Specific acceptance criteria]',
        user_experience_goals='[UX goals and expectations]',
        functional_requirements='[Detailed functional requirements]',
        non_functional_requirements='[Performance, scalability, security requirements]',
        integration_requirements='[Integration points and dependencies]',
        user_metrics='[User-facing metrics to track]',
        performance_metrics='[Performance metrics and targets]',
        technical_metrics='[Technical metrics and KPIs]',
        must_have_features='[Essential features - cannot ship without]',
        should_have_features='[Important features - should include if possible]',
        could_have_features='[Nice-to-have features - include if time permits]',
        wont_have_features='[Features explicitly out of scope]',
        requirements_status=RequirementsStatus.DRAFT,
    )
    return requirements.build_markdown()


def generate_project_plan_template() -> str:
    project_plan = ProjectPlan(
        project_name='[Project Name]',
        project_vision='[High-level vision statement]',
        project_mission='[Mission and purpose]',
        project_timeline='[Overall timeline]',
        project_budget='[Budget allocation]',
        primary_objectives='[Primary project objectives]',
        success_metrics='[Success measurement criteria]',
        key_performance_indicators='[KPIs to track]',
        included_features='[Features included in scope]',
        excluded_features='[Features explicitly excluded]',
        project_assumptions='[Key assumptions]',
        project_constraints='[Constraints and limitations]',
        project_sponsor='[Project sponsor]',
        key_stakeholders='[Key stakeholders]',
        end_users='[End user groups]',
        work_breakdown='[Work breakdown structure]',
        phases_overview='[Project phases overview]',
        project_dependencies='[Dependencies and prerequisites]',
        team_structure='[Team structure and roles]',
        technology_requirements='[Technology requirements]',
        infrastructure_needs='[Infrastructure needs]',
        identified_risks='[Identified risks]',
        mitigation_strategies='[Risk mitigation strategies]',
        contingency_plans='[Contingency plans]',
        quality_standards='[Quality standards]',
        testing_strategy='[Testing strategy]',
        acceptance_criteria='[Project acceptance criteria]',
        reporting_structure='[Reporting structure]',
        meeting_schedule='[Meeting schedule]',
        documentation_standards='[Documentation standards]',
        project_status=ProjectStatus.DRAFT,
    )
    return project_plan.build_markdown()


def generate_critic_feedback_template() -> str:
    feedback = CriticFeedback(
        loop_id='[Loop identifier]',
        critic_agent=CriticAgent.ANALYST_CRITIC,
        iteration=1,
        overall_score=75,
        assessment_summary='[Overall assessment summary]',
        detailed_feedback='[Detailed analysis and feedback]',
        key_issues=['[Issue 1]', '[Issue 2]', '[Issue 3]'],
        recommendations=['[Recommendation 1]', '[Recommendation 2]', '[Recommendation 3]'],
    )
    return feedback.build_markdown()


def main() -> None:
    templates = {
        'roadmap_template.md': generate_roadmap_template(),
        'build_plan_template.md': generate_build_plan_template(),
        'feature_requirements_template.md': generate_feature_requirements_template(),
        'project_plan_template.md': generate_project_plan_template(),
        'critic_feedback_template.md': generate_critic_feedback_template(),
    }

    print('Generated templates from Pydantic models:')
    print('=' * 50)

    for filename, content in templates.items():
        print(f'\n## {filename}')
        print('-' * len(filename))
        print(content)
        print('\n' + '=' * 50)


if __name__ == '__main__':
    main()
