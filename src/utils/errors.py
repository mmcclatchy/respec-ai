from fastmcp.exceptions import ToolError


class LoopError(Exception): ...


class LoopNotFoundError(LoopError): ...


class LoopAlreadyExistsError(LoopError): ...


class LoopInvalidError(LoopError): ...


class LoopValidationError(ToolError):
    def __init__(self, field: str, message: str):
        super().__init__(f'Invalid {field}: {message}')
        self.field = field


class LoopStateError(ToolError):
    def __init__(self, loop_id: str, operation: str, details: str):
        super().__init__(f'Loop {operation} failed for {loop_id}: {details}')
        self.loop_id = loop_id


class RoadmapError(Exception): ...


class RoadmapNotFoundError(RoadmapError): ...


class SpecNotFoundError(RoadmapError): ...


class ProjectPlanError(Exception): ...


class ProjectPlanNotFoundError(ProjectPlanError): ...


class RoadmapValidationError(ToolError):
    def __init__(self, field: str, message: str):
        super().__init__(f'Invalid {field}: {message}')
        self.field = field
