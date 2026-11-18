"""Test-only section-name helpers shared by the phase template guards.

`_extract_content_from_raw_markdown` takes the first `## ` line containing a section's name
(F27 trap 1), so an H2 whose name sits inside another H2's name captures the wrong content with
no error.

Phase 4 retired nine detail fields from generation (phase-4-agent-ready-brief.md, Scope 2). The
model keeps them, so a hand-written section still round-trips, but no prompt teaches or checks
them any more.
"""

import re
from collections.abc import Iterable

from src.models.phase import Phase


RETIRED_FIELDS = (
    'architecture',
    'technology_stack',
    'system_design_additional',
    'functional_requirements',
    'non_functional_requirements',
    'development_plan',
    'testing_strategy',
    'implementation_additional',
    'integration_context',
)

# The strategic plan's own H2, which the architect reads; it shares a word with a retired field.
_PLAN_HEADING = 'Architecture Direction'


def retired_section_mentions(template: str) -> set[str]:
    text = template.replace(_PLAN_HEADING, '')
    names = {Phase.HEADER_FIELD_MAPPING[field][-1] for field in RETIRED_FIELDS}
    found = {name for name in names if re.search(rf'\b{re.escape(name)}\b', text)}
    return found | ({'NFR'} if re.search(r'\bNFRs?\b', text) else set())


def mapped_h2_names() -> set[str]:
    return {header_path[0] for header_path in Phase.HEADER_FIELD_MAPPING.values()}


def h2_collisions(names: Iterable[str]) -> set[frozenset[str]]:
    unique = set(names)
    return {frozenset((a, b)) for a in unique for b in unique if a != b and (a in b or b in a)}
