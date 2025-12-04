import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from services.models.feedback import CriticFeedback
from services.utils.enums import HealthState, LoopStatus, LoopType, OperationStatus
from services.models.roadmap import Roadmap


class MCPRoadMapResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: LoopStatus
    roadmap: Roadmap


class MCPResponse(BaseModel):
    id: str
    status: LoopStatus
    message: str = ''
    char_length: int | None = None


class OperationResponse(BaseModel):
    id: str
    status: OperationStatus
    message: str = ''


class LoopState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    loop_type: LoopType
    status: LoopStatus = LoopStatus.INITIALIZED
    current_score: int = Field(default=0, ge=0, le=100)
    score_history: list[int] = Field(default_factory=list)
    iteration: int = Field(default=1, ge=1)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    feedback_history: list[CriticFeedback] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def mcp_response(self) -> MCPResponse:
        return MCPResponse(id=self.id, status=self.status)

    def is_first_iteration(self) -> bool:
        return self.iteration == 1

    def increment_iteration(self) -> int:
        self.iteration += 1
        return self.iteration

    def add_score(self, score: int) -> None:
        self.score_history.append(score)
        self.current_score = score

    def decide_next_loop_action(self) -> MCPResponse:
        if self.current_score >= self.loop_type.threshold:
            self.status = LoopStatus.COMPLETED
            return self.mcp_response

        if (
            self.iteration > 0 and self.iteration % self.loop_type.checkpoint_frequency == 0
        ) or self._detect_stagnation():
            self.status = LoopStatus.USER_INPUT
            return self.mcp_response

        self.status = LoopStatus.REFINE
        return self.mcp_response

    def _calculate_improvement(self, scores_ago: int = 1) -> int:
        if not self.score_history:
            return 0
        score_ago_index = scores_ago * -1
        return self.score_history[score_ago_index] - self.score_history[score_ago_index - 1]

    def _detect_stagnation(self) -> bool:
        if len(self.score_history) < 3:
            return False

        threshold = self.loop_type.improvement_threshold
        recent_improvements: list[int] = [
            self._calculate_improvement(2),
            self._calculate_improvement(1),
        ]
        return all(improvement < threshold for improvement in recent_improvements)

    def add_feedback(self, feedback: CriticFeedback) -> None:
        self.feedback_history.append(feedback)
        self.add_score(feedback.quality_score)
        self.updated_at = datetime.now()

        # Update status to indicate loop is active with feedback
        if self.status == LoopStatus.INITIALIZED:
            self.status = LoopStatus.IN_PROGRESS

    def get_recent_feedback(self, count: int = 5) -> list[CriticFeedback]:
        return self.feedback_history[-count:] if self.feedback_history else []


class HealthStatus(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    status: HealthState = HealthState.HEALTHY
    tools_count: int = 0
    error: str | None = None
