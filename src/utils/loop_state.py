import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.models.roadmap import Roadmap
from src.utils.enums import HealthState, LoopStatus, LoopType, OperationStatus


class MCPRoadMapResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: LoopStatus
    roadmap: Roadmap


class MCPResponse(BaseModel):
    id: str
    status: LoopStatus
    message: str = ''
    char_length: int | None = None
    current_score: int = 0
    iteration: int = 0


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
    _BLOCKING_MARKERS = ('[blocking]', '[severity:p0]', 'severity=p0', '**[p0]**')
    _MARKER_BLOCKER_GATE_CRITICS = {
        CriticAgent.REVIEW_CONSOLIDATOR,
        CriticAgent.CODING_STANDARDS_REVIEWER,
    }
    _DOCUMENT_BLOCKER_STAGNATION_CRITICS = {
        CriticAgent.PLAN_CRITIC,
        CriticAgent.ANALYST_CRITIC,
        CriticAgent.ROADMAP_CRITIC,
        CriticAgent.PHASE_CRITIC,
        CriticAgent.TASK_CRITIC,
    }

    @property
    def mcp_response(self) -> MCPResponse:
        return MCPResponse(
            id=self.id,
            status=self.status,
            current_score=self.current_score,
            iteration=self.iteration,
        )

    def add_score(self, score: int) -> None:
        self.score_history.append(score)
        self.current_score = score

    def decide_next_loop_action(self) -> MCPResponse:
        if self.current_score >= self.loop_type.threshold and not self._latest_feedback_has_blockers():
            self.status = LoopStatus.COMPLETED
            return self.mcp_response

        if (
            self.iteration > 0 and self.iteration % self.loop_type.checkpoint_frequency == 0
        ) or self._detect_stagnation():
            self.status = LoopStatus.USER_INPUT
            return self.mcp_response

        self.status = LoopStatus.REFINE
        return self.mcp_response

    def _latest_feedback_has_blockers(self) -> bool:
        if not self.feedback_history:
            return False

        latest_feedback = self.feedback_history[-1]
        return bool(self._effective_blockers_for_feedback(latest_feedback))

    def _effective_blockers_for_feedback(self, feedback: CriticFeedback) -> list[str]:
        structured_blockers = [blocker.strip() for blocker in feedback.blockers if blocker.strip()]
        if structured_blockers:
            return structured_blockers

        if feedback.critic_agent not in self._MARKER_BLOCKER_GATE_CRITICS:
            return []

        feedback_text = '\n'.join(
            [
                feedback.assessment_summary,
                feedback.detailed_feedback,
                *feedback.key_issues,
                *feedback.recommendations,
            ]
        ).lower()
        if any(marker in feedback_text for marker in self._BLOCKING_MARKERS):
            return ['marker-blocker-detected']
        return []

    def _calculate_improvement(self, scores_ago: int = 1) -> int:
        if not self.score_history:
            return 0
        score_ago_index = scores_ago * -1
        return self.score_history[score_ago_index] - self.score_history[score_ago_index - 1]

    def _detect_stagnation(self) -> bool:
        score_stagnant = False
        if len(self.score_history) >= 3:
            threshold = self.loop_type.improvement_threshold
            recent_improvements: list[int] = [
                self._calculate_improvement(2),
                self._calculate_improvement(1),
            ]
            score_stagnant = all(improvement < threshold for improvement in recent_improvements)

        blocker_stagnant = self._uses_document_blocker_stagnation() and self._detect_blocker_stagnation()
        return score_stagnant or blocker_stagnant

    def _uses_document_blocker_stagnation(self) -> bool:
        if not self.feedback_history:
            return False
        return self.feedback_history[-1].critic_agent in self._DOCUMENT_BLOCKER_STAGNATION_CRITICS

    def _detect_blocker_stagnation(self, window: int = 3) -> bool:
        if len(self.feedback_history) < window:
            return False

        recent_feedback = self.feedback_history[-window:]
        normalized_blocker_sets: list[frozenset[str]] = []
        for feedback in recent_feedback:
            blockers = self._effective_blockers_for_feedback(feedback)
            normalized_blockers = frozenset(blocker.strip().lower() for blocker in blockers if blocker.strip())
            if not normalized_blockers:
                return False
            normalized_blocker_sets.append(normalized_blockers)

        return all(blocker_set == normalized_blocker_sets[0] for blocker_set in normalized_blocker_sets[1:])

    def add_feedback(self, feedback: CriticFeedback) -> None:
        self.feedback_history.append(feedback)
        self.add_score(feedback.quality_score)
        self.iteration = len(self.feedback_history)
        self.updated_at = datetime.now()

        # Update status to indicate loop is active with feedback
        if self.status == LoopStatus.INITIALIZED:
            self.status = LoopStatus.IN_PROGRESS

    def upsert_feedback(self, feedback: CriticFeedback) -> None:
        for index, existing in enumerate(self.feedback_history):
            if existing.critic_agent == feedback.critic_agent and existing.iteration == feedback.iteration:
                self.feedback_history[index] = feedback
                if index < len(self.score_history):
                    self.score_history[index] = feedback.quality_score
                else:
                    self.score_history.append(feedback.quality_score)
                self.current_score = self.score_history[-1] if self.score_history else 0
                self.iteration = len(self.feedback_history)
                self.updated_at = datetime.now()
                if self.status == LoopStatus.INITIALIZED:
                    self.status = LoopStatus.IN_PROGRESS
                return

        self.add_feedback(feedback)

    def get_recent_feedback(self, count: int = 5) -> list[CriticFeedback]:
        return self.feedback_history[-count:] if self.feedback_history else []


class HealthStatus(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    status: HealthState = HealthState.HEALTHY
    tools_count: int = 0
    error: str | None = None
