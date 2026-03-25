from pydantic import Field

from .base import MCPModel


class ConversationContext(MCPModel):
    problem_statement: str
    desired_outcome: str
    success_metrics: str
    business_drivers: str
    stakeholder_needs: str
    organizational_constraints: str
    functional_requirements: list[str] = Field(default_factory=list)
    user_experience_requirements: list[str] = Field(default_factory=list)
    integration_requirements: list[str] = Field(default_factory=list)
    performance_requirements: list[str] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)
    technical_constraints: list[str] = Field(default_factory=list)
    timeline_constraints: list[str] = Field(default_factory=list)
    resource_constraints: list[str] = Field(default_factory=list)
    business_constraints: list[str] = Field(default_factory=list)
    must_have_features: list[str] = Field(default_factory=list)
    nice_to_have_features: list[str] = Field(default_factory=list)
    technology_context: str = ''
    total_stages_completed: int = 4
    key_insights: list[str] = Field(default_factory=list)
    areas_of_emphasis: list[str] = Field(default_factory=list)
    user_engagement_level: str = 'medium'

    def build_markdown(self) -> str:
        functional_md = (
            '\n'.join([f'- {req}' for req in self.functional_requirements])
            if self.functional_requirements
            else '- [Specific capability or feature requirement]'
        )
        user_experience_md = (
            '\n'.join([f'- {req}' for req in self.user_experience_requirements])
            if self.user_experience_requirements
            else '- [User-facing requirement or expectation]'
        )
        integration_md = (
            '\n'.join([f'- {req}' for req in self.integration_requirements])
            if self.integration_requirements
            else '- [System integration or interoperability requirement]'
        )
        performance_md = (
            '\n'.join([f'- {req}' for req in self.performance_requirements])
            if self.performance_requirements
            else '- [Performance target or constraint]'
        )
        security_md = (
            '\n'.join([f'- {req}' for req in self.security_requirements])
            if self.security_requirements
            else '- [Security requirement or compliance need]'
        )
        technical_constraints_md = (
            '\n'.join([f'- {constraint}' for constraint in self.technical_constraints])
            if self.technical_constraints
            else '- [Technical limitation or requirement]'
        )
        timeline_md = (
            '\n'.join([f'- {constraint}' for constraint in self.timeline_constraints])
            if self.timeline_constraints
            else '- [Time-related constraint or deadline]'
        )
        resource_md = (
            '\n'.join([f'- {constraint}' for constraint in self.resource_constraints])
            if self.resource_constraints
            else '- [Budget, staffing, or resource limitation]'
        )
        business_constraints_md = (
            '\n'.join([f'- {constraint}' for constraint in self.business_constraints])
            if self.business_constraints
            else '- [Business policy or operational constraint]'
        )
        must_have_md = (
            '\n'.join([f'- {feature}' for feature in self.must_have_features])
            if self.must_have_features
            else '- [Critical requirement that must be delivered]'
        )
        nice_to_have_md = (
            '\n'.join([f'- {feature}' for feature in self.nice_to_have_features])
            if self.nice_to_have_features
            else "- [Desirable feature that adds value but isn't critical]"
        )
        key_insights_md = (
            '\n'.join([f'- {insight}' for insight in self.key_insights])
            if self.key_insights
            else '[Main discoveries or understandings from the conversation]'
        )
        areas_of_emphasis_md = (
            '\n'.join([f'- {area}' for area in self.areas_of_emphasis])
            if self.areas_of_emphasis
            else '[Topics or aspects the user focused on most]'
        )

        return f"""## Vision and Objectives

### Problem Statement
{self.problem_statement}

### Desired Outcome
{self.desired_outcome}

### Success Metrics
{self.success_metrics}

## Business Context

### Business Drivers
{self.business_drivers}

### Stakeholder Needs
{self.stakeholder_needs}

### Organizational Constraints
{self.organizational_constraints}

## Requirements

### Functional Requirements
{functional_md}

### User Experience Requirements
{user_experience_md}

### Integration Requirements
{integration_md}

### Performance Requirements
{performance_md}

### Security Requirements
{security_md}

### Technical Constraints
{technical_constraints_md}

## Constraints

### Timeline Constraints
{timeline_md}

### Resource Constraints
{resource_md}

### Business Constraints
{business_constraints_md}

## Priorities

### Must-Have Features
{must_have_md}

### Nice-to-Have Features
{nice_to_have_md}

## Technology Context

### Preferred Stack
{self.technology_context if self.technology_context else '[Technology preferences and decisions from discussion]'}

## Conversation Summary

- **Total Stages Completed**: {self.total_stages_completed}
- **Key Insights**: {key_insights_md}
- **Areas of Emphasis**: {areas_of_emphasis_md}
- **User Engagement Level**: {self.user_engagement_level}
"""
