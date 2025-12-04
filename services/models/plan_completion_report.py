from typing import ClassVar

from pydantic import field_validator

from .base import MCPModel


class PlanCompletionStatus(str):
    USER_ACCEPTED = 'User-accepted (human-driven decision)'
    ANALYST_VALIDATED = 'Analyst validation completed'
    COMPLETED = 'Planning phase completed'


class UserDecision(str):
    CONTINUE_CONVERSATION = 'continue_conversation'
    REFINE_PLAN = 'refine_plan'
    ACCEPT_PLAN = 'accept_plan'


class AnalystLoopStatus(str):
    REFINE = 'refine'
    USER_INPUT = 'user_input'
    COMPLETED = 'completed'


class PlanCompletionReport(MCPModel):
    # Class configuration
    TITLE_PATTERN: ClassVar[str] = '# Strategic Plan Output'
    TITLE_FIELD: ClassVar[str] = 'report_title'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'final_plan_score': ('Plan Quality', 'Final Plan Score'),
        'plan_completion_status': ('Plan Quality', 'Plan Completion Status'),
        'user_decision': ('Plan Quality', 'User Decision'),
        'final_analyst_score': ('Analyst Validation', 'Final Analyst Score'),
        'analyst_completion_status': ('Analyst Validation', 'Analyst Completion Status'),
        'analyst_loop_result': ('Analyst Validation', 'Analyst Loop Result'),
        'strategic_plan_document': ('Strategic Plan Document',),
        'structured_objectives': ('Structured Objectives',),
        'next_steps': ('Next Steps',),
        'analyst_loop_id': ('Metadata', 'Analyst Loop ID'),
        'completion_timestamp': ('Metadata', 'Timestamp'),
    }

    # Model fields with defaults
    report_title: str = 'Strategic Plan Output'
    final_plan_score: str = '0'
    plan_completion_status: str = PlanCompletionStatus.USER_ACCEPTED
    user_decision: str = UserDecision.ACCEPT_PLAN
    final_analyst_score: str = '0'
    analyst_completion_status: str = AnalystLoopStatus.COMPLETED
    analyst_loop_result: str = AnalystLoopStatus.COMPLETED
    strategic_plan_document: str = '[Strategic plan document content]'
    structured_objectives: str = '[Structured business objectives analysis]'
    next_steps: str = """1. Review the strategic plan for accuracy
2. Proceed with technical specification using: /spec-ai-spec
3. The structured objectives will feed directly into spec-architect"""
    analyst_loop_id: str = '[Analyst loop ID from MCP server]'
    completion_timestamp: str = '[Current date/time]'

    @field_validator('final_plan_score', 'final_analyst_score')
    @classmethod
    def validate_score_format(cls, v: str) -> str:
        if v and not v.startswith('${') and v not in ['0', '[Score]']:
            try:
                score = int(v)
                if not 0 <= score <= 100:
                    raise ValueError('Score must be between 0 and 100')
            except ValueError as e:
                if 'invalid literal' in str(e):
                    raise ValueError(f'Score must be a valid integer or template variable, got: {v}')
                raise
        return v

    @field_validator('user_decision')
    @classmethod
    def validate_user_decision(cls, v: str) -> str:
        valid_decisions = {UserDecision.CONTINUE_CONVERSATION, UserDecision.REFINE_PLAN, UserDecision.ACCEPT_PLAN}
        if v and not v.startswith('${') and v not in valid_decisions:
            raise ValueError(f'User decision must be one of: {", ".join(valid_decisions)}')
        return v

    @field_validator('analyst_completion_status', 'analyst_loop_result')
    @classmethod
    def validate_analyst_status(cls, v: str) -> str:
        valid_statuses = {AnalystLoopStatus.REFINE, AnalystLoopStatus.USER_INPUT, AnalystLoopStatus.COMPLETED}
        if v and not v.startswith('${') and v not in valid_statuses:
            raise ValueError(f'Analyst status must be one of: {", ".join(valid_statuses)}')
        return v

    @field_validator('plan_completion_status')
    @classmethod
    def validate_plan_status(cls, v: str) -> str:
        valid_statuses = {
            PlanCompletionStatus.USER_ACCEPTED,
            PlanCompletionStatus.ANALYST_VALIDATED,
            PlanCompletionStatus.COMPLETED,
        }
        if v and not v.startswith('${') and v not in valid_statuses:
            raise ValueError(f'Plan completion status must be one of: {", ".join(valid_statuses)}')
        return v

    def build_markdown(self) -> str:
        return f"""# {self.report_title}

## Plan Quality

### Final Plan Score
{self.final_plan_score}%

### Plan Completion Status
{self.plan_completion_status}

### User Decision
{self.user_decision}

## Analyst Validation

### Final Analyst Score
{self.final_analyst_score}%

### Analyst Completion Status
{self.analyst_completion_status}

### Analyst Loop Result
{self.analyst_loop_result}

## Strategic Plan Document
{self.strategic_plan_document}

## Structured Objectives
{self.structured_objectives}

## Next Steps
{self.next_steps}

## Metadata

### Analyst Loop ID
{self.analyst_loop_id}

### Timestamp
{self.completion_timestamp}
"""
