from datetime import datetime
from typing import Self

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from pydantic import Field, field_validator

from .base import MCPModel
from .enums import CriticAgent


class CriticFeedback(MCPModel):
    loop_id: str
    critic_agent: CriticAgent
    iteration: int
    overall_score: int
    assessment_summary: str
    detailed_feedback: str
    key_issues: list[str]
    recommendations: list[str]
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('overall_score')
    @classmethod
    def validate_score_range(cls, score: int) -> int:
        if not (0 <= score <= 100):
            raise ValueError('Overall score must be between 0 and 100')
        return score

    @property
    def quality_score(self) -> int:
        return self.overall_score

    @classmethod
    def parse_markdown(cls, markdown: str) -> Self:
        md = MarkdownIt('commonmark')
        tree = SyntaxTreeNode(md.parse(markdown))

        fields = {}
        critic_name = 'UNKNOWN'

        # Extract title
        for node in cls._find_nodes_by_type(tree, 'heading'):
            if node.tag != 'h1':
                continue
            title_text = cls._extract_text_content(node)
            if 'Critic Feedback:' in title_text:
                critic_name = title_text.split(':', 1)[1].strip()
                break

        # Extract all field data from lists
        for item in cls._find_nodes_by_type(tree, 'list_item'):
            text = cls._extract_text_content(item).strip()
            if ':' not in text:
                continue
            field_part, value_part = text.split(':', 1)
            field_name = field_part.strip().lower().replace(' ', '_').replace('-', '_')
            field_value = value_part.strip()

            # Map field names to model field names
            field_mapping = {'critic': 'critic_agent', 'timestamp': 'timestamp', 'status': 'status'}
            model_field_name = field_mapping.get(field_name, field_name)
            fields[model_field_name] = field_value

        # Extract detailed feedback
        detailed_feedback = cls._extract_content_by_header_path(tree, ('Analysis',))

        # Extract key issues and recommendations
        key_issues = []
        recommendations = []

        # Extract issues and recommendations using a special list extraction method
        key_issues = cls._extract_list_items_by_header_path(tree, ('Issues and Recommendations', 'Key Issues'))
        recommendations = cls._extract_list_items_by_header_path(
            tree, ('Issues and Recommendations', 'Recommendations')
        )

        # Set defaults for missing fields
        if 'loop_id' not in fields:
            fields['loop_id'] = 'unknown'
        if 'iteration' not in fields:
            fields['iteration'] = '1'
        if 'overall_score' not in fields:
            fields['overall_score'] = '0'
        if 'assessment_summary' not in fields:
            fields['assessment_summary'] = 'Assessment Summary not provided'
        if not detailed_feedback:
            detailed_feedback = 'Detailed Feedback not provided'
        if 'critic_agent' not in fields:
            fields['critic_agent'] = critic_name

        # Parse critic agent enum - map common names to actual enum values
        agent_name = fields['critic_agent'].upper()
        agent_mapping = {
            'ANALYST': CriticAgent.ANALYST_CRITIC,
            'ANALYST-CRITIC': CriticAgent.ANALYST_CRITIC,
            'PLAN': CriticAgent.PLAN_CRITIC,
            'PLAN-CRITIC': CriticAgent.PLAN_CRITIC,
            'ROADMAP': CriticAgent.ROADMAP_CRITIC,
            'ROADMAP-CRITIC': CriticAgent.ROADMAP_CRITIC,
            'SPEC': CriticAgent.SPEC_CRITIC,
            'SPEC-CRITIC': CriticAgent.SPEC_CRITIC,
            'BUILD': CriticAgent.BUILD_CRITIC,
            'BUILD-CRITIC': CriticAgent.BUILD_CRITIC,
            'BUILD-REVIEWER': CriticAgent.BUILD_REVIEWER,
            'REVIEWER': CriticAgent.BUILD_REVIEWER,
        }

        critic_agent = agent_mapping.get(agent_name, CriticAgent.ANALYST_CRITIC)

        # Parse iteration and score
        try:
            iteration = int(fields['iteration'])
        except ValueError:
            iteration = 1

        try:
            overall_score = int(fields['overall_score'].split('/')[0])
        except ValueError:
            overall_score = 0

        return cls(
            loop_id=fields['loop_id'],
            critic_agent=critic_agent,
            iteration=iteration,
            overall_score=overall_score,
            assessment_summary=fields['assessment_summary'],
            detailed_feedback=detailed_feedback,
            key_issues=key_issues,
            recommendations=recommendations,
        )

    def build_markdown(self) -> str:
        issues_md = '\n'.join([f'- {issue}' for issue in self.key_issues]) if self.key_issues else '- None identified'
        recommendations_md = (
            '\n'.join([f'- {rec}' for rec in self.recommendations]) if self.recommendations else '- None provided'
        )

        return f"""# Critic Feedback: {self.critic_agent.value.upper()}

## Assessment Summary
- **Loop ID**: {self.loop_id}
- **Iteration**: {self.iteration}
- **Overall Score**: {self.overall_score}
- **Assessment Summary**: {self.assessment_summary}

## Analysis

{self.detailed_feedback}

## Issues and Recommendations

### Key Issues

{issues_md}

### Recommendations

{recommendations_md}

## Metadata
- **Critic**: {self.critic_agent.value.upper()}
- **Timestamp**: {self.timestamp.isoformat()}
- **Status**: completed
"""
