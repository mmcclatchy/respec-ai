"""Tool enums defining all valid tools across external platforms, built-in Claude Code tools, and Specter MCP tools."""

from enum import Enum


class ExternalPlatformTool(Enum):
    # Linear Server Tools
    LINEAR_CREATE_ISSUE = 'mcp__linear-server__create_issue'
    LINEAR_GET_ISSUE = 'mcp__linear-server__get_issue'
    LINEAR_UPDATE_ISSUE = 'mcp__linear-server__update_issue'
    LINEAR_CREATE_COMMENT = 'mcp__linear-server__create_comment'
    LINEAR_CREATE_PROJECT = 'mcp__linear-server__create_project'
    LINEAR_GET_DOCUMENT = 'mcp__linear-server__get_document'
    LINEAR_LIST_ISSUES = 'mcp__linear-server__list_issues'
    LINEAR_LIST_DOCUMENTS = 'mcp__linear-server__list_documents'
    LINEAR_GET_PROJECT = 'mcp__linear-server__get_project'
    LINEAR_LIST_PROJECTS = 'mcp__linear-server__list_projects'
    LINEAR_UPDATE_PROJECT = 'mcp__linear-server__update_project'
    LINEAR_CREATE_PROJECT_LABEL = 'mcp__linear-server__create_project_label'
    LINEAR_LIST_PROJECT_LABELS = 'mcp__linear-server__list_project_labels'
    LINEAR_LIST_TEAMS = 'mcp__linear-server__list_teams'
    LINEAR_GET_TEAM = 'mcp__linear-server__get_team'
    LINEAR_LIST_USERS = 'mcp__linear-server__list_users'
    LINEAR_GET_USER = 'mcp__linear-server__get_user'
    LINEAR_LIST_CYCLES = 'mcp__linear-server__list_cycles'
    LINEAR_LIST_ISSUE_STATUSES = 'mcp__linear-server__list_issue_statuses'
    LINEAR_GET_ISSUE_STATUS = 'mcp__linear-server__get_issue_status'
    LINEAR_LIST_ISSUE_LABELS = 'mcp__linear-server__list_issue_labels'
    LINEAR_CREATE_ISSUE_LABEL = 'mcp__linear-server__create_issue_label'
    LINEAR_LIST_COMMENTS = 'mcp__linear-server__list_comments'
    LINEAR_SEARCH_DOCUMENTATION = 'mcp__linear-server__search_documentation'

    # GitHub Tools (placeholder - would be implemented when GitHub platform is added)
    GITHUB_CREATE_ISSUE = 'mcp__github__create_issue'
    GITHUB_GET_ISSUE = 'mcp__github__get_issue'
    GITHUB_UPDATE_ISSUE = 'mcp__github__update_issue'
    GITHUB_CREATE_COMMENT = 'mcp__github__create_comment'
    GITHUB_CREATE_PROJECT = 'mcp__github__create_project'
    GITHUB_GET_FILE = 'mcp__github__get_file'
    GITHUB_UPDATE_FILE = 'mcp__github__update_file'
    GITHUB_LIST_FILES = 'mcp__github__list_files'


class BuiltInTool(Enum):
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

    # Project Management
    TODO_WRITE = 'TodoWrite'
    EXIT_PLAN_MODE = 'ExitPlanMode'
    SLASH_COMMAND = 'SlashCommand'


class SpecterMCPTool(Enum):
    # Loop Management Tools
    INITIALIZE_REFINEMENT_LOOP = 'mcp__specter__initialize_refinement_loop'
    DECIDE_LOOP_NEXT_ACTION = 'mcp__specter__decide_loop_next_action'
    GET_LOOP_STATUS = 'mcp__specter__get_loop_status'
    LIST_ACTIVE_LOOPS = 'mcp__specter__list_active_loops'
    GET_LOOP_FEEDBACK_SUMMARY = 'mcp__specter__get_loop_feedback_summary'
    GET_LOOP_IMPROVEMENT_ANALYSIS = 'mcp__specter__get_loop_improvement_analysis'
    GET_PREVIOUS_OBJECTIVE_FEEDBACK = 'mcp__specter__get_previous_objective_feedback'
    STORE_CURRENT_OBJECTIVE_FEEDBACK = 'mcp__specter__store_current_objective_feedback'

    # Feedback Management Tools
    STORE_CRITIC_FEEDBACK = 'mcp__specter__store_critic_feedback'
    STORE_USER_FEEDBACK = 'mcp__specter__store_user_feedback'
    GET_FEEDBACK = 'mcp__specter__get_feedback'
    STORE_CURRENT_ANALYSIS = 'mcp__specter__store_current_analysis'
    GET_PREVIOUS_ANALYSIS = 'mcp__specter__get_previous_analysis'

    # Project Plan Tools
    CREATE_PROJECT_PLAN = 'mcp__specter__create_project_plan'
    STORE_PROJECT_PLAN = 'mcp__specter__store_project_plan'
    GET_PROJECT_PLAN_MARKDOWN = 'mcp__specter__get_project_plan_markdown'
    LIST_PROJECT_PLANS = 'mcp__specter__list_project_plans'
    DELETE_PROJECT_PLAN = 'mcp__specter__delete_project_plan'

    # Roadmap Management Tools
    CREATE_ROADMAP = 'mcp__specter__create_roadmap'
    GET_ROADMAP = 'mcp__specter__get_roadmap'

    # Spec Management Tools
    GET_SPEC_MARKDOWN = 'mcp__specter__get_spec_markdown'
    STORE_SPEC = 'mcp__specter__store_spec'
    LIST_SPECS = 'mcp__specter__list_specs'
    DELETE_SPEC = 'mcp__specter__delete_spec'
    LINK_LOOP_TO_SPEC = 'mcp__specter__link_loop_to_spec'
    UNLINK_LOOP = 'mcp__specter__unlink_loop'

    # Build Plan Tools
    STORE_BUILD_PLAN = 'mcp__specter__store_build_plan'
    GET_BUILD_PLAN_MARKDOWN = 'mcp__specter__get_build_plan_markdown'
    LIST_BUILD_PLANS = 'mcp__specter__list_build_plans'
    DELETE_BUILD_PLAN = 'mcp__specter__delete_build_plan'

    # Plan Completion Report Tools
    CREATE_PLAN_COMPLETION_REPORT = 'mcp__specter__create_plan_completion_report'
    STORE_PLAN_COMPLETION_REPORT = 'mcp__specter__store_plan_completion_report'
    GET_PLAN_COMPLETION_REPORT_MARKDOWN = 'mcp__specter__get_plan_completion_report_markdown'
    UPDATE_PLAN_COMPLETION_REPORT = 'mcp__specter__update_plan_completion_report'
    LIST_PLAN_COMPLETION_REPORTS = 'mcp__specter__list_plan_completion_reports'
    DELETE_PLAN_COMPLETION_REPORT = 'mcp__specter__delete_plan_completion_report'


class AbstractOperation(Enum):
    # Spec Management Operations
    CREATE_SPEC_TOOL = 'create_spec_tool'
    GET_SPEC_TOOL = 'get_spec_tool'
    UPDATE_SPEC_TOOL = 'update_spec_tool'
    COMMENT_SPEC_TOOL = 'comment_spec_tool'

    # Project Management Operations
    CREATE_PROJECT_EXTERNAL = 'create_project_external'
    CREATE_PROJECT_COMPLETION_EXTERNAL = 'create_project_completion_external'

    # Plan Management Operations
    GET_PROJECT_PLAN_TOOL = 'get_project_plan_tool'
    UPDATE_PROJECT_PLAN_TOOL = 'update_project_plan_tool'

    # Spec Listing Operations
    LIST_PROJECT_SPECS_TOOL = 'list_project_specs_tool'


class CommandTemplate(Enum):
    PLAN = 'specter-plan'
    SPEC = 'specter-spec'
    BUILD = 'specter-build'
    ROADMAP = 'specter-roadmap'
    PLAN_CONVERSATION = 'specter-plan-conversation'


ToolEnums = ExternalPlatformTool | BuiltInTool | SpecterMCPTool
