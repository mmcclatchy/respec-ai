from enum import Enum

from pydantic import BaseModel


# Contract between PhaseTools.update and the phase architect template, which matches this
# text exactly to decide whether to rewrite the named headings - one definition, imported by both.
CONTENT_LOSS_WARNING = 'WARNING: content lost on write'

# Contract between PhaseTools.validate and the phase command's hand-edit menu, which must not
# offer to proceed with an edit whose content-loss lines carry this text.
UNSTORABLE_DOCUMENT = 'The document cannot be stored'


class StructuralCheck(str, Enum):
    SEAM_PATH_NOT_IN_MODULE_LAYOUT = 'seam-path-not-in-module-layout'
    SEAM_ENTRY_MALFORMED = 'seam-entry-malformed'
    SEAM_SIGNATURE_UNPARSEABLE = 'seam-signature-unparseable'
    TEST_LIST_EMPTY = 'test-list-empty'
    TEST_ENTRY_WITHOUT_BEHAVIOR = 'test-entry-without-behavior'
    DECISION_ENTRY_MALFORMED = 'decision-entry-malformed'
    SETTLED_ENTRY_MALFORMED = 'settled-entry-malformed'
    SECTION_NAME_OVERLAP = 'section-name-overlap'
    DUPLICATE_ID = 'duplicate-id'
    SETTLED_DECISION_STILL_OPEN = 'settled-decision-still-open'
    DANGLING_REFERENCE = 'dangling-reference'
    IMPLEMENTATION_SECTION_MISSING = 'implementation-section-missing'
    IMPLEMENTATION_STEP_HEADING_MALFORMED = 'implementation-step-heading-malformed'
    IMPLEMENTATION_NO_STEPS = 'implementation-no-steps'
    IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED = 'implementation-checklist-item-malformed'
    IMPLEMENTATION_STEP_UNVERIFIED = 'implementation-step-unverified'


class FindingOwner(str, Enum):
    ARCHITECT = 'architect'
    ORCHESTRATOR = 'orchestrator'


class CitedPathKind(str, Enum):
    READ = 'read'
    CONSTRAINT = 'constraint'
    BEST_PRACTICES = 'best-practices'


class StructuralFinding(BaseModel):
    check: StructuralCheck
    location: str
    subject: str
    # The element at fault when a subject has several, e.g. "Option B" or "rejected". Prompts and
    # accept-as-is SDs key a finding as "<check> <subject>", plus " [<part>]" when part is set.
    part: str = ''
    owner: FindingOwner
    detail: str


class CitedPath(BaseModel):
    path: str
    kind: CitedPathKind
    cited_in: str
