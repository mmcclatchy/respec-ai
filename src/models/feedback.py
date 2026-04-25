from datetime import datetime
from typing import ClassVar, Self

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from pydantic import BaseModel, Field, field_validator, model_validator

from .base import MCPModel
from .enums import CriticAgent, Priority


class CriticFeedback(MCPModel):
    EMPTY_BLOCKER_SENTINELS: ClassVar[frozenset[str]] = frozenset(
        {
            'none',
            'none identified',
            'none provided',
            'no blockers',
            'no active blockers',
            'n/a',
            'na',
        }
    )

    loop_id: str
    critic_agent: CriticAgent
    iteration: int
    overall_score: int
    assessment_summary: str
    detailed_feedback: str
    key_issues: list[str]
    blockers: list[str] = Field(default_factory=list)
    recommendations: list[str]
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('overall_score')
    @classmethod
    def validate_score_range(cls, score: int) -> int:
        if not (0 <= score <= 100):
            raise ValueError('Overall score must be between 0 and 100')
        return score

    @field_validator('blockers')
    @classmethod
    def validate_blockers_are_actionable(cls, blockers: list[str]) -> list[str]:
        invalid_blockers = cls.invalid_blocker_values(blockers)
        if invalid_blockers:
            invalid_values = ', '.join(repr(blocker) for blocker in invalid_blockers)
            raise ValueError(
                'Blockers must be actionable non-empty strings; use [] when no blockers exist. '
                f'Remove invalid blocker entries: {invalid_values}'
            )
        return blockers

    @property
    def quality_score(self) -> int:
        return self.overall_score

    @classmethod
    def is_empty_blocker_sentinel(cls, value: str) -> bool:
        normalized = value.strip().lower().strip(' .:-')
        return normalized in cls.EMPTY_BLOCKER_SENTINELS

    @classmethod
    def is_invalid_blocker_value(cls, value: str) -> bool:
        return not value.strip() or cls.is_empty_blocker_sentinel(value)

    @classmethod
    def invalid_blocker_values(cls, blockers: list[str]) -> list[str]:
        return [blocker for blocker in blockers if cls.is_invalid_blocker_value(blocker)]

    @classmethod
    def parse_markdown(cls, markdown: str) -> Self:
        if not markdown or not markdown.strip():
            raise ValueError('Feedback markdown cannot be empty')

        md = MarkdownIt('commonmark')
        tree = SyntaxTreeNode(md.parse(markdown))

        fields: dict[str, str] = {}
        critic_name: str | None = None

        # Extract title
        for node in cls._find_nodes_by_type(tree, 'heading'):
            if node.tag != 'h1':
                continue
            title_text = cls._extract_text_content(node)
            if 'Critic Feedback:' in title_text:
                critic_name = title_text.split(':', 1)[1].strip()
                break
        if not critic_name:
            raise ValueError('Missing critic feedback title header')

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
        if not detailed_feedback:
            raise ValueError('Missing Analysis section content')

        # Extract key issues and recommendations
        key_issues = cls._extract_list_items_by_header_path(tree, ('Issues and Recommendations', 'Key Issues'))
        blockers = cls._extract_list_items_by_header_path(tree, ('Issues and Recommendations', 'Blockers'))
        recommendations = cls._extract_list_items_by_header_path(
            tree, ('Issues and Recommendations', 'Recommendations')
        )

        # Fail fast if core fields are missing.
        required_fields = ('loop_id', 'iteration', 'overall_score', 'assessment_summary')
        missing_fields = [field for field in required_fields if not fields.get(field)]
        if missing_fields:
            missing = ', '.join(missing_fields)
            raise ValueError(f'Missing required assessment fields: {missing}')

        critic_agent = CriticAgent.from_header(fields.get('critic_agent') or critic_name)

        # Parse iteration and score
        try:
            iteration = int(fields['iteration'])
        except ValueError as exc:
            raise ValueError(f'Invalid iteration value: {fields["iteration"]}') from exc

        score_token = fields['overall_score'].split('/')[0].strip()
        try:
            overall_score = int(score_token)
        except ValueError as exc:
            raise ValueError(f'Invalid overall score value: {fields["overall_score"]}') from exc

        return cls(
            loop_id=fields['loop_id'],
            critic_agent=critic_agent,
            iteration=iteration,
            overall_score=overall_score,
            assessment_summary=fields['assessment_summary'],
            detailed_feedback=detailed_feedback,
            key_issues=key_issues,
            blockers=blockers,
            recommendations=recommendations,
        )

    def build_markdown(self) -> str:
        issues_md = '\n'.join([f'- {issue}' for issue in self.key_issues]) if self.key_issues else '- None identified'
        blockers_md = '\n'.join([f'- {blocker}' for blocker in self.blockers])
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

### Blockers

{blockers_md}

### Recommendations

{recommendations_md}

## Metadata
- **Critic**: {self.critic_agent.value.upper()}
- **Timestamp**: {self.timestamp.isoformat()}
- **Status**: completed
"""


class ReviewFinding(BaseModel):
    priority: Priority
    feedback: str


class ReviewerResult(BaseModel):
    loop_id: str
    review_iteration: int
    reviewer_name: CriticAgent
    feedback_markdown: str
    score: int
    max_score: int
    blockers: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('score')
    @classmethod
    def validate_score_range(cls, score: int) -> int:
        if score < 0:
            raise ValueError('Reviewer score must be >= 0')
        return score

    @field_validator('max_score')
    @classmethod
    def validate_max_score(cls, max_score: int) -> int:
        if max_score <= 0:
            raise ValueError('Reviewer max_score must be > 0')
        return max_score

    @field_validator('blockers')
    @classmethod
    def validate_blockers_are_actionable(cls, blockers: list[str]) -> list[str]:
        invalid_blockers = CriticFeedback.invalid_blocker_values(blockers)
        if invalid_blockers:
            invalid_values = ', '.join(repr(blocker) for blocker in invalid_blockers)
            raise ValueError(
                'Reviewer blockers must be actionable non-empty strings; use [] when no blockers exist. '
                f'Remove invalid blocker entries: {invalid_values}'
            )
        return blockers

    @model_validator(mode='after')
    def validate_score_within_max(self) -> Self:
        if self.score > self.max_score:
            raise ValueError('Reviewer score must be <= max_score')
        return self

    @property
    def normalized_score(self) -> int:
        return int(round((self.score / self.max_score) * 100))
