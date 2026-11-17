from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.mcp.tools.base import EXACTLY_ONE_INPUT, DocumentToolsInterface, content_loss_response
from src.models.document_validation import CONTENT_LOSS_WARNING, UNSTORABLE_DOCUMENT, StructuralFinding
from src.models.phase import Phase
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError, PhaseNotFoundError
from src.utils.loop_state import DocumentValidationResponse, MCPResponse
from src.utils.phase_structure import (
    check_implementation_structure,
    check_phase_structure,
    drop_accepted_findings,
    extract_cited_paths,
)
from src.utils.state_manager.base import FROZEN_DISCARD_WARNING, FROZEN_FIELD_DEFAULTS, FROZEN_PHASES_FIELDS


KEY_MODE_MESSAGE = 'Content loss is not checked in key mode: the stored phase has already been parsed.'
STRUCTURE_NOT_PARSED = 'structure: document does not parse'
IMPLEMENTATION_NOT_PASSED = 'implementation.md: not passed'
IMPLEMENTATION_NOT_CHECKED = 'implementation.md: not checked, because the phase document does not parse'
CITED_PATHS_NOT_CHECKED = (
    'cited-paths-exist: the server cannot see the project filesystem; verify paths_to_verify on the host'
)


def with_discard_warning(message: str, discarded: list[str]) -> str:
    if not discarded:
        return message

    return (
        f'{message}\n'
        f'{FROZEN_DISCARD_WARNING} ({", ".join(discarded)}). '
        f'These fields are set once at iteration 0 and preserved thereafter; '
        f'the stored phase still holds its previous values for them.'
    )


def with_content_loss_warning(message: str, lost: list[str]) -> str:
    if not lost:
        return message

    return f'{message}\n{CONTENT_LOSS_WARNING} ({"; ".join(lost)}). The phase was stored without this text.'


def one_line_reason(error: ValueError) -> str:
    if not isinstance(error, ValidationError):
        return ' '.join(str(error).split())

    return '; '.join(
        f'{".".join(str(part) for part in detail["loc"]) or "document"}: {detail["msg"]}' for detail in error.errors()
    )


def unstorable_response(
    lost: list[str], error: ValueError, implementation_markdown: str | None
) -> DocumentValidationResponse:
    message = '\n'.join(
        [
            'Content loss detected:',
            *[f'- {line}' for line in lost],
            f'- {UNSTORABLE_DOCUMENT}: {one_line_reason(error)}',
        ]
    )
    implementation_skipped = (
        IMPLEMENTATION_NOT_PASSED if implementation_markdown is None else IMPLEMENTATION_NOT_CHECKED
    )
    return DocumentValidationResponse(
        id='validate',
        status=LoopStatus.USER_INPUT,
        message=message,
        skipped_checks=[STRUCTURE_NOT_PARSED, implementation_skipped, CITED_PATHS_NOT_CHECKED],
    )


def with_structural_checks(
    response: DocumentValidationResponse, phase: Phase, implementation_markdown: str | None
) -> DocumentValidationResponse:
    structural, accepted_structural = drop_accepted_findings(check_phase_structure(phase), phase)
    implementation: list[StructuralFinding] = []
    accepted_implementation: list[str] = []
    implementation_skipped: list[str] = []
    if implementation_markdown is None:
        implementation_skipped.append(IMPLEMENTATION_NOT_PASSED)
    else:
        implementation, accepted_implementation = drop_accepted_findings(
            check_implementation_structure(implementation_markdown, phase), phase
        )

    return response.model_copy(
        update={
            'structural_findings': structural,
            'implementation_findings': implementation,
            'paths_to_verify': extract_cited_paths(phase),
            'skipped_checks': [
                *implementation_skipped,
                *accepted_structural,
                *accepted_implementation,
                CITED_PATHS_NOT_CHECKED,
            ],
        }
    )


class PhaseTools(DocumentToolsInterface):
    document_model = Phase

    async def validate(
        self, content: str | None = None, key: str | None = None, implementation_markdown: str | None = None
    ) -> DocumentValidationResponse:
        """Check phase content (content loss plus structure) or the stored phase (structure only).

        Structural findings never change status or message: those report content loss alone, so
        the hand-edit menu never shows a structural problem to the user (F29).
        """
        if content and not key:
            return self.validate_content(content, implementation_markdown)
        if key and not content:
            return await self.validate_stored(key, implementation_markdown)
        raise ToolError(EXACTLY_ONE_INPUT)

    def validate_content(self, content: str, implementation_markdown: str | None) -> DocumentValidationResponse:
        lost = Phase.find_content_loss(content)
        try:
            phase = Phase.parse_markdown(content)
        except (ValueError, ValidationError) as error:
            return unstorable_response(lost, error, implementation_markdown)

        return with_structural_checks(content_loss_response(lost), phase, implementation_markdown)

    async def validate_stored(self, key: str, implementation_markdown: str | None) -> DocumentValidationResponse:
        plan_name, phase_name = self._parse_key(key)
        try:
            phase = await self.state.get_phase(plan_name, phase_name)
        except PhaseNotFoundError as e:
            raise ResourceError(str(e))

        response = DocumentValidationResponse(id=key, status=LoopStatus.COMPLETED, message=KEY_MODE_MESSAGE)
        return with_structural_checks(response, phase, implementation_markdown)

    async def discarded_frozen_fields(
        self, plan_name: str, phase: Phase, allow_frozen_field_edits: bool = False
    ) -> list[str]:
        """Report which frozen Overview fields a pending write will not change.

        The state managers preserve frozen fields silently and still return success, so
        without this the caller cannot tell a stored edit from a discarded one (F1b).
        Probes the LIVE phase because that is exactly the row store_phase preserves from.
        """
        if allow_frozen_field_edits:
            return []

        try:
            existing = await self.state.get_phase(plan_name, phase.phase_name)
        except PhaseNotFoundError:
            return []

        existing_data = existing.model_dump()
        incoming = phase.model_dump()

        return [
            field
            for field in FROZEN_PHASES_FIELDS
            if existing_data[field] != FROZEN_FIELD_DEFAULTS[field] and incoming[field] != existing_data[field]
        ]

    async def get_phase_by_path_or_loop(self, path: str | None = None, loop_id: str | None = None) -> MCPResponse:
        try:
            if loop_id:
                loop_state = await self.state.get_loop(loop_id)
                phase = await self.state.get_phase_by_loop(loop_id)
                content = phase.build_markdown()
                char_length = len(content)
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message=content,
                    char_length=char_length,
                )

            if path:
                parts = path.split('/')
                if len(parts) != 2:
                    raise ToolError(f'Invalid phase path format: {path} (expected: plan-name/phase-name)')
                plan_name, phase_name = parts
                phase = await self.state.get_phase(plan_name, phase_name)
                content = phase.build_markdown()
                char_length = len(content)
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=content,
                    char_length=char_length,
                )

            raise ToolError('Either path OR loop_id must be provided')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist or is not linked to a document')
        except PhaseNotFoundError as e:
            raise ResourceError(str(e))
        except ValueError as e:
            raise ResourceError(str(e))
        except (ResourceError, ToolError):
            raise
        except Exception as e:
            raise ToolError(f'Failed to retrieve phase: {str(e)}')

    async def list_phases(self, plan_name: str) -> MCPResponse:
        if not plan_name:
            raise ToolError('parent_path (plan_name) is required for listing phases')

        try:
            phase_names = await self.state.list_phases(plan_name)
            paths = [f'{plan_name}/{name}' for name in phase_names]

            if not paths:
                return MCPResponse(
                    id='phase',
                    status=LoopStatus.COMPLETED,
                    message=f'No phase documents found under {plan_name}',
                )

            paths_str = ', '.join(paths)
            return MCPResponse(
                id='phase',
                status=LoopStatus.COMPLETED,
                message=f'Found {len(paths)} phase document{"s" if len(paths) != 1 else ""} under {plan_name}: {paths_str}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list phases: {str(e)}')

    async def delete_phase(self, plan_name: str, phase_name: str) -> MCPResponse:
        if not plan_name or not phase_name:
            raise ToolError('Plan name and phase name cannot be empty')

        try:
            was_deleted = await self.state.delete_phase(plan_name, phase_name)
            path = f'{plan_name}/{phase_name}'

            if was_deleted:
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=f'Deleted phase document at {path}',
                )
            else:
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=f'phase document not found at {path}',
                )
        except Exception as e:
            raise ToolError(f'Failed to delete phase: {str(e)}')

    async def link_loop_to_phase(self, loop_id: str, plan_name: str, phase_name: str) -> MCPResponse:
        if not loop_id or not plan_name or not phase_name:
            raise ToolError('Loop ID, plan name, and phase name cannot be empty')

        try:
            await self.state.link_loop_to_phase(loop_id, plan_name, phase_name)
            loop_state = await self.state.get_loop(loop_id)
            path = f'{plan_name}/{phase_name}'
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Linked loop {loop_id} to phase document at {path}',
            )
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Failed to link loop to phase: {str(e)}')

    # Standardized interface methods (new)

    def _parse_key(self, key: str) -> tuple[str, str]:
        parts = key.split('/')
        if len(parts) != 2:
            raise ToolError(f'Invalid phase key: {key} (expected: plan-name/phase-name)')
        return parts[0], parts[1]

    async def store(self, key: str, content: str, allow_frozen_field_edits: bool = False) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            phase = Phase.parse_markdown(content)
            discarded = await self.discarded_frozen_fields(plan_name, phase, allow_frozen_field_edits)
            await self.state.store_phase(plan_name, phase, allow_frozen_field_edits=allow_frozen_field_edits)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=with_discard_warning(phase_name, discarded))
        except ValidationError as e:
            raise ToolError(f'Invalid phase markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to store phase: {str(e)}')

    async def get(self, key: str | None = None, loop_id: str | None = None, include_phases: bool = True) -> MCPResponse:
        return await self.get_phase_by_path_or_loop(path=key, loop_id=loop_id)

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        if not parent_key:
            raise ToolError('parent_key (plan_name) is required for listing phases')

        return await self.list_phases(parent_key)

    async def update(self, key: str, content: str, allow_frozen_field_edits: bool = False) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            lost = Phase.find_content_loss(content)
            phase = Phase.parse_markdown(content)
            discarded = await self.discarded_frozen_fields(plan_name, phase, allow_frozen_field_edits)
            result = await self.state.update_phase(
                plan_name, phase_name, phase, allow_frozen_field_edits=allow_frozen_field_edits
            )

            message = with_content_loss_warning(with_discard_warning(result, discarded), lost)
            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=message)
        except ValidationError as e:
            raise ToolError(f'Invalid phase markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to update phase: {str(e)}')

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            return await self.delete_phase(plan_name, phase_name)
        except Exception as e:
            raise ToolError(f'Failed to delete phase: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        if not loop_id or not key:
            raise ToolError('Loop ID and key cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            return await self.link_loop_to_phase(loop_id, plan_name, phase_name)
        except Exception as e:
            raise ToolError(f'Failed to link loop to phase: {str(e)}')
