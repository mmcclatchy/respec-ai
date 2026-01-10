from abc import ABC, abstractmethod


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific instruction generation.

    All methods return strings that get interpolated into command/agent templates.
    NO methods execute operations - they only generate instruction text.

    Methods use domain terminology (plan/phase/task), NOT platform terms.
    Concrete implementations map to platform-specific instruction patterns internally.
    """

    @property
    @abstractmethod
    def plan_sync_instructions(self) -> str: ...

    @property
    @abstractmethod
    def phase_sync_instructions(self) -> str: ...

    @property
    @abstractmethod
    def task_sync_instructions(self) -> str: ...

    @property
    @abstractmethod
    def plan_discovery_instructions(self) -> str: ...

    @property
    @abstractmethod
    def phase_discovery_instructions(self) -> str: ...

    @property
    @abstractmethod
    def task_discovery_instructions(self) -> str: ...

    @property
    @abstractmethod
    def plan_location_hint(self) -> str: ...

    @property
    @abstractmethod
    def phase_location_hint(self) -> str: ...

    @property
    @abstractmethod
    def task_location_hint(self) -> str: ...

    @property
    @abstractmethod
    def coding_standards_location(self) -> str: ...

    @property
    @abstractmethod
    def coding_standards_read_instruction(self) -> str: ...

    @property
    @abstractmethod
    def create_plan_tool(self) -> str: ...

    @property
    @abstractmethod
    def retrieve_plan_tool(self) -> str: ...

    @property
    @abstractmethod
    def update_plan_tool(self) -> str: ...

    @property
    @abstractmethod
    def create_plan_completion_tool(self) -> str: ...

    @property
    @abstractmethod
    def create_phase_tool(self) -> str: ...

    @property
    @abstractmethod
    def retrieve_phase_tool(self) -> str: ...

    @property
    @abstractmethod
    def update_phase_tool(self) -> str: ...

    @property
    @abstractmethod
    def comment_phase_tool(self) -> str: ...

    @property
    @abstractmethod
    def create_task_tool(self) -> str: ...

    @property
    @abstractmethod
    def retrieve_task_tool(self) -> str: ...

    @property
    @abstractmethod
    def update_task_tool(self) -> str: ...

    @property
    @abstractmethod
    def list_phases_tool(self) -> str: ...

    @property
    @abstractmethod
    def list_tasks_tool(self) -> str: ...

    @property
    @abstractmethod
    def config_location(self) -> str: ...

    @property
    @abstractmethod
    def phase_discovery_pattern(self) -> str: ...

    @property
    @abstractmethod
    def phase_resource_pattern(self) -> str: ...

    @property
    @abstractmethod
    def task_resource_pattern(self) -> str: ...

    @property
    @abstractmethod
    def plan_resource_example(self) -> str: ...

    @property
    @abstractmethod
    def phase_resource_example(self) -> str: ...

    @property
    @abstractmethod
    def task_location_setup(self) -> str: ...

    @property
    @abstractmethod
    def discovery_tool_invocation(self) -> str: ...

    @property
    @abstractmethod
    def platform_tool_documentation(self) -> str: ...
