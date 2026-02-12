"""Tool enums defining all valid tools across external platforms, built-in Claude Code tools, and respec-ai MCP tools."""

from enum import StrEnum


# Tool prefixes - defined outside classes to avoid being picked up as enum members
_LINEAR_PREFIX = 'mcp__linear-server__'
_GITHUB_PREFIX = 'mcp__github__'
_RESPEC_AI_PREFIX = 'mcp__respec-ai__'
_RESPEC_AGENT_PREFIX = 'respec-'


class ExternalPlatformTool(StrEnum):
    # Linear Server Tools
    LINEAR_CREATE_ISSUE = f'{_LINEAR_PREFIX}create_issue'
    LINEAR_GET_ISSUE = f'{_LINEAR_PREFIX}get_issue'
    LINEAR_UPDATE_ISSUE = f'{_LINEAR_PREFIX}update_issue'
    LINEAR_CREATE_COMMENT = f'{_LINEAR_PREFIX}create_comment'
    LINEAR_CREATE_PROJECT = f'{_LINEAR_PREFIX}create_project'
    LINEAR_GET_DOCUMENT = f'{_LINEAR_PREFIX}get_document'
    LINEAR_LIST_ISSUES = f'{_LINEAR_PREFIX}list_issues'
    LINEAR_LIST_DOCUMENTS = f'{_LINEAR_PREFIX}list_documents'
    LINEAR_GET_PROJECT = f'{_LINEAR_PREFIX}get_project'
    LINEAR_LIST_PROJECTS = f'{_LINEAR_PREFIX}list_projects'
    LINEAR_UPDATE_PROJECT = f'{_LINEAR_PREFIX}update_project'
    LINEAR_CREATE_PROJECT_LABEL = f'{_LINEAR_PREFIX}create_project_label'
    LINEAR_LIST_PROJECT_LABELS = f'{_LINEAR_PREFIX}list_project_labels'
    LINEAR_LIST_TEAMS = f'{_LINEAR_PREFIX}list_teams'
    LINEAR_GET_TEAM = f'{_LINEAR_PREFIX}get_team'
    LINEAR_LIST_USERS = f'{_LINEAR_PREFIX}list_users'
    LINEAR_GET_USER = f'{_LINEAR_PREFIX}get_user'
    LINEAR_LIST_CYCLES = f'{_LINEAR_PREFIX}list_cycles'
    LINEAR_LIST_ISSUE_STATUSES = f'{_LINEAR_PREFIX}list_issue_statuses'
    LINEAR_GET_ISSUE_STATUS = f'{_LINEAR_PREFIX}get_issue_status'
    LINEAR_LIST_ISSUE_LABELS = f'{_LINEAR_PREFIX}list_issue_labels'
    LINEAR_CREATE_ISSUE_LABEL = f'{_LINEAR_PREFIX}create_issue_label'
    LINEAR_LIST_COMMENTS = f'{_LINEAR_PREFIX}list_comments'
    LINEAR_SEARCH_DOCUMENTATION = f'{_LINEAR_PREFIX}search_documentation'

    # GitHub Tools (placeholder - would be implemented when GitHub platform is added)
    GITHUB_CREATE_ISSUE = f'{_GITHUB_PREFIX}create_issue'
    GITHUB_GET_ISSUE = f'{_GITHUB_PREFIX}get_issue'
    GITHUB_UPDATE_ISSUE = f'{_GITHUB_PREFIX}update_issue'
    GITHUB_CREATE_COMMENT = f'{_GITHUB_PREFIX}create_comment'
    GITHUB_CREATE_PROJECT = f'{_GITHUB_PREFIX}create_project'
    GITHUB_GET_FILE = f'{_GITHUB_PREFIX}get_file'
    GITHUB_UPDATE_FILE = f'{_GITHUB_PREFIX}update_file'
    GITHUB_LIST_FILES = f'{_GITHUB_PREFIX}list_files'


class BuiltInTool(StrEnum):
    # File Operations
    READ = 'Read'
    WRITE = 'Write'
    EDIT = 'Edit'
    MULTI_EDIT = 'MultiEdit'
    NOTEBOOK_EDIT = 'NotebookEdit'

    # Search and Discovery
    GLOB = 'Glob'
    GREP = 'Grep'

    # Agent and Task Management
    TASK = 'Task'

    # System Operations
    BASH = 'Bash'
    BASH_OUTPUT = 'BashOutput'
    KILL_SHELL = 'KillShell'

    # Web Operations
    WEB_FETCH = 'WebFetch'
    WEB_SEARCH = 'WebSearch'

    # Plan Management
    TODO_WRITE = 'TodoWrite'
    EXIT_PLAN_MODE = 'ExitPlanMode'
    SLASH_COMMAND = 'SlashCommand'

    # User Interaction
    ASK_USER_QUESTION = 'AskUserQuestion'


class RespecAITool(StrEnum):
    # Loop Management Tools
    INITIALIZE_REFINEMENT_LOOP = f'{_RESPEC_AI_PREFIX}initialize_refinement_loop'
    DECIDE_LOOP_NEXT_ACTION = f'{_RESPEC_AI_PREFIX}decide_loop_next_action'
    GET_LOOP_STATUS = f'{_RESPEC_AI_PREFIX}get_loop_status'
    LIST_ACTIVE_LOOPS = f'{_RESPEC_AI_PREFIX}list_active_loops'
    GET_LOOP_FEEDBACK_SUMMARY = f'{_RESPEC_AI_PREFIX}get_loop_feedback_summary'
    GET_LOOP_IMPROVEMENT_ANALYSIS = f'{_RESPEC_AI_PREFIX}get_loop_improvement_analysis'

    # Feedback Management Tools
    STORE_CRITIC_FEEDBACK = f'{_RESPEC_AI_PREFIX}store_critic_feedback'
    STORE_USER_FEEDBACK = f'{_RESPEC_AI_PREFIX}store_user_feedback'
    GET_FEEDBACK = f'{_RESPEC_AI_PREFIX}get_feedback'
    STORE_CURRENT_ANALYSIS = f'{_RESPEC_AI_PREFIX}store_current_analysis'
    GET_PREVIOUS_ANALYSIS = f'{_RESPEC_AI_PREFIX}get_previous_analysis'

    # Document Management Tools (Generic)
    STORE_DOCUMENT = f'{_RESPEC_AI_PREFIX}store_document'
    GET_DOCUMENT = f'{_RESPEC_AI_PREFIX}get_document'
    LIST_DOCUMENTS = f'{_RESPEC_AI_PREFIX}list_documents'
    UPDATE_DOCUMENT = f'{_RESPEC_AI_PREFIX}update_document'
    DELETE_DOCUMENT = f'{_RESPEC_AI_PREFIX}delete_document'
    LINK_LOOP_TO_DOCUMENT = f'{_RESPEC_AI_PREFIX}link_loop_to_document'

    # Roadmap-specific Tools (dedicated to prevent loop_id misuse)
    GET_ROADMAP = f'{_RESPEC_AI_PREFIX}get_roadmap'
    CREATE_ROADMAP = f'{_RESPEC_AI_PREFIX}create_roadmap'


class AbstractOperation(StrEnum):
    # Phase Management Operations
    CREATE_PHASE_TOOL = 'create_phase_tool'
    GET_PHASE_TOOL = 'get_phase_tool'
    UPDATE_PHASE_TOOL = 'update_phase_tool'
    COMMENT_PHASE_TOOL = 'comment_phase_tool'
    LIST_PROJECT_PHASES_TOOL = 'list_project_phases_tool'

    # Task Management Operations
    CREATE_TASK_TOOL = 'create_task_tool'
    LIST_PHASE_TASKS_TOOL = 'list_phase_tasks_tool'

    # Plan Management Operations
    CREATE_PROJECT_EXTERNAL = 'create_project_external'
    CREATE_PROJECT_COMPLETION_EXTERNAL = 'create_project_completion_external'

    # Plan Management Operations
    GET_PROJECT_PLAN_TOOL = 'get_plan_tool'
    UPDATE_PROJECT_PLAN_TOOL = 'update_plan_tool'


class RespecAIAgent(StrEnum):
    # Phase workflow agents
    PHASE_ARCHITECT = f'{_RESPEC_AGENT_PREFIX}phase-architect'
    PHASE_CRITIC = f'{_RESPEC_AGENT_PREFIX}phase-critic'

    # Plan workflow agents
    PLAN_CONVERSATION = f'{_RESPEC_AGENT_PREFIX}plan-conversation'
    PLAN_CRITIC = f'{_RESPEC_AGENT_PREFIX}plan-critic'
    PLAN_ANALYST = f'{_RESPEC_AGENT_PREFIX}plan-analyst'
    ANALYST_CRITIC = f'{_RESPEC_AGENT_PREFIX}analyst-critic'

    # Task workflow agents
    TASK_PLANNER = f'{_RESPEC_AGENT_PREFIX}task-planner'
    TASK_PLAN_CRITIC = f'{_RESPEC_AGENT_PREFIX}task-plan-critic'
    CREATE_TASK = f'{_RESPEC_AGENT_PREFIX}create-task'

    # Code workflow agents
    PHASE_PLANNER = f'{_RESPEC_AGENT_PREFIX}phase-planner'
    TASK_CRITIC = f'{_RESPEC_AGENT_PREFIX}task-critic'
    CODER = f'{_RESPEC_AGENT_PREFIX}coder'
    CODE_REVIEWER = f'{_RESPEC_AGENT_PREFIX}code-reviewer'

    # Review team agents
    AUTOMATED_QUALITY_CHECKER = f'{_RESPEC_AGENT_PREFIX}automated-quality-checker'
    SPEC_ALIGNMENT_REVIEWER = f'{_RESPEC_AGENT_PREFIX}spec-alignment-reviewer'
    FRONTEND_REVIEWER = f'{_RESPEC_AGENT_PREFIX}frontend-reviewer'
    BACKEND_API_REVIEWER = f'{_RESPEC_AGENT_PREFIX}backend-api-reviewer'
    DATABASE_REVIEWER = f'{_RESPEC_AGENT_PREFIX}database-reviewer'
    INFRASTRUCTURE_REVIEWER = f'{_RESPEC_AGENT_PREFIX}infrastructure-reviewer'
    REVIEW_CONSOLIDATOR = f'{_RESPEC_AGENT_PREFIX}review-consolidator'

    # Roadmap workflow agents
    ROADMAP = f'{_RESPEC_AGENT_PREFIX}roadmap'
    ROADMAP_CRITIC = f'{_RESPEC_AGENT_PREFIX}roadmap-critic'
    CREATE_PHASE = f'{_RESPEC_AGENT_PREFIX}create-phase'


class RespecAICommand(StrEnum):
    PLAN = 'respec-plan'
    PHASE = 'respec-phase'
    TASK = 'respec-task'
    CODE = 'respec-code'
    ROADMAP = 'respec-roadmap'
    PLAN_CONVERSATION = 'respec-plan-conversation'


ToolEnums = ExternalPlatformTool | BuiltInTool | RespecAITool
