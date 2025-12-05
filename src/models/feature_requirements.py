from typing import ClassVar

from .base import MCPModel
from .enums import RequirementsStatus


class FeatureRequirements(MCPModel):
    # Class configuration for MCPModel
    TITLE_PATTERN: ClassVar[str] = '# Feature Requirements'
    TITLE_FIELD: ClassVar[str] = 'project_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'feature_description': ('Overview', 'Feature Description'),
        'problem_statement': ('Overview', 'Problem Statement'),
        'target_users': ('Overview', 'Target Users'),
        'business_value': ('Overview', 'Business Value'),
        'user_stories': ('Requirements', 'User Stories'),
        'acceptance_criteria': ('Requirements', 'Acceptance Criteria'),
        'user_experience_goals': ('Requirements', 'User Experience Goals'),
        'functional_requirements': ('Technical Specifications', 'Functional Requirements'),
        'non_functional_requirements': ('Technical Specifications', 'Non-Functional Requirements'),
        'integration_requirements': ('Technical Specifications', 'Integration Requirements'),
        'user_metrics': ('Metrics', 'User Metrics'),
        'performance_metrics': ('Metrics', 'Performance Metrics'),
        'technical_metrics': ('Metrics', 'Technical Metrics'),
        'must_have_features': ('Feature Prioritization', 'Must Have'),
        'should_have_features': ('Feature Prioritization', 'Should Have'),
        'could_have_features': ('Feature Prioritization', 'Could Have'),
        'wont_have_features': ('Feature Prioritization', "Won't Have"),
        'requirements_status': ('Metadata', 'Status'),
    }

    # Model fields with defaults
    project_name: str = 'Unnamed Project'
    feature_description: str = 'Feature Description not specified'
    problem_statement: str = 'Problem Statement not specified'
    target_users: str = 'Target Users not specified'
    business_value: str = 'Business Value not specified'
    user_stories: str = 'User Stories not specified'
    acceptance_criteria: str = 'Acceptance Criteria not specified'
    user_experience_goals: str = 'User Experience Goals not specified'
    functional_requirements: str = 'Functional Requirements not specified'
    non_functional_requirements: str = 'Non-Functional Requirements not specified'
    integration_requirements: str = 'Integration Requirements not specified'
    user_metrics: str = 'User Metrics not specified'
    performance_metrics: str = 'Performance Metrics not specified'
    technical_metrics: str = 'Technical Metrics not specified'
    must_have_features: str = 'Must Have Features not specified'
    should_have_features: str = 'Should Have Features not specified'
    could_have_features: str = 'Could Have Features not specified'
    wont_have_features: str = "Won't Have Features not specified"
    requirements_status: RequirementsStatus = RequirementsStatus.DRAFT

    def build_markdown(self) -> str:
        return f"""{self.TITLE_PATTERN}: {self.project_name}

## Overview

### Feature Description
{self.feature_description}

### Problem Statement
{self.problem_statement}

### Target Users
{self.target_users}

### Business Value
{self.business_value}

## Requirements

### User Stories
{self.user_stories}

### Acceptance Criteria
{self.acceptance_criteria}

### User Experience Goals
{self.user_experience_goals}

## Technical Specifications

### Functional Requirements
{self.functional_requirements}

### Non-Functional Requirements
{self.non_functional_requirements}

### Integration Requirements
{self.integration_requirements}

## Metrics

### User Metrics
{self.user_metrics}

### Performance Metrics
{self.performance_metrics}

### Technical Metrics
{self.technical_metrics}

## Feature Prioritization

### Must Have
{self.must_have_features}

### Should Have
{self.should_have_features}

### Could Have
{self.could_have_features}

### Won't Have
{self.wont_have_features}

## Metadata

### Status
{self.requirements_status.value}
"""
