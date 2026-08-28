import re

from src.models.enums import CriticAgent
from src.models.phase import Phase
from src.utils.language_extensions import is_frontend_path

FRONTEND_DOMAIN_POOL_FLOOR = 15.0
FRONTEND_DOMAIN_POOL_CEILING = 35.0

# A UX Contract is a frontend signal even when the Skeleton Index/Module Layout paths it
# accompanies don't (yet) skew frontend -- e.g. a phase still shaping its design. Floors the
# ratio rather than replacing it so a phase that is *also* path-dominant frontend keeps that
# higher signal. Judgment call, not a derivation -- revisit against real phases (see phase-6
# doc's "One judgment call").
UX_CONTRACT_FRONTEND_RATIO_FLOOR = 0.3

_UX_CONTRACT_MARKER = '#### UX Contract'

# Domain-keyed groups, not a flat set (decisions.md, "Domain weights scale with phase shape") --
# so a future second frontend-domain reviewer splits the frontend domain's own share instead of
# re-dividing the whole pool among one more member, which would silently steal weight from
# backend/database/infrastructure (B6).
SPECIALIST_DOMAIN_GROUPS: dict[str, frozenset[CriticAgent]] = {
    'frontend': frozenset({CriticAgent.FRONTEND_REVIEWER}),
    'backend': frozenset({CriticAgent.BACKEND_API_REVIEWER}),
    'database': frozenset({CriticAgent.DATABASE_REVIEWER}),
    'infrastructure': frozenset({CriticAgent.INFRASTRUCTURE_REVIEWER}),
}

# Mirrors skeleton_generator._BULLET_PATH: a Skeleton Index / Module Layout entry always opens
# with a backtick-quoted path. Deliberately does not reuse parse_skeleton_index -- that also
# parses the per-language signature grammar (phase 2) and can raise on a malformed entry: weight
# computation must never fail review consolidation over a formatting quirk it doesn't need to
# understand.
_BULLET_PATH = re.compile(r'^-\s*`(?P<path>[^`]+)`')


def _extract_bullet_paths(markdown: str | None) -> list[str]:
    if not markdown:
        return []
    paths = []
    for line in markdown.splitlines():
        match = _BULLET_PATH.match(line.strip())
        if match:
            paths.append(match.group('path'))
    return paths


def compute_frontend_ratio(phase: Phase | None) -> float:
    """Fraction (0.0-1.0) of the Phase design that is frontend, via phase 1's extension map.

    Classifies every `### Skeleton Index` / `### Module Layout` path as frontend or not
    (`is_frontend_path` -- the only domain the extension map can tell apart; backend/database/
    infrastructure are not separable by extension and are intentionally not attempted here, to
    avoid a second classification path alongside phase 1's -- F1/F14). A `#### UX Contract`
    under Design Shape - Additional Sections is an additional frontend signal, applied as a
    floor rather than counted as a path.
    """
    if phase is None:
        return 0.0

    paths = [*_extract_bullet_paths(phase.skeleton_index), *_extract_bullet_paths(phase.module_layout)]
    design_shape_additional = phase.design_shape_additional or ''
    has_ux_contract = _UX_CONTRACT_MARKER in design_shape_additional

    if not paths:
        ratio = 0.0
    else:
        ratio = sum(1 for path in paths if is_frontend_path(path)) / len(paths)

    return max(ratio, UX_CONTRACT_FRONTEND_RATIO_FLOOR) if has_ux_contract else ratio


def compute_domain_pool_size(frontend_ratio: float) -> float:
    """Linear interpolation between the floor and ceiling, monotonic in frontend_ratio (B7)."""
    return FRONTEND_DOMAIN_POOL_FLOOR + (FRONTEND_DOMAIN_POOL_CEILING - FRONTEND_DOMAIN_POOL_FLOOR) * frontend_ratio


def compute_phase1_weights(
    core_weights: dict[CriticAgent, float],
    active_reviewers: set[CriticAgent],
    frontend_ratio: float,
) -> dict[CriticAgent, float]:
    """Split core + domain weight across active reviewers for a phase-1 (design/code) review.

    The domain pool grows with frontend_ratio (floor when there is no frontend signal, up to
    the ceiling for an all-frontend phase) and core scales down proportionally, preserving core
    reviewers' ratios to each other -- so a backend-only phase (frontend_ratio == 0, no active
    frontend reviewer) reproduces the pre-phase-6 fixed weights exactly (B1). Within the domain
    pool, the frontend domain's share tracks frontend_ratio and the remaining share splits
    evenly across whichever other domains (backend/database/infrastructure) are active; each
    domain's own share then splits evenly across that domain's active members, so adding a
    second frontend-domain reviewer never moves the other domains' weights (B6).
    """
    frontend_active = bool(SPECIALIST_DOMAIN_GROUPS['frontend'] & active_reviewers)
    effective_frontend_ratio = frontend_ratio if frontend_active else 0.0
    domain_pool_size = compute_domain_pool_size(effective_frontend_ratio)

    core_total_at_floor = sum(core_weights.values())
    reference_total = core_total_at_floor + FRONTEND_DOMAIN_POOL_FLOOR
    core_total = reference_total - domain_pool_size
    scale = core_total / core_total_at_floor if core_total_at_floor else 0.0

    weights: dict[CriticAgent, float] = {
        reviewer: weight * scale for reviewer, weight in core_weights.items() if reviewer in active_reviewers
    }

    active_groups = {
        domain: members
        for domain, group in SPECIALIST_DOMAIN_GROUPS.items()
        if (members := group & active_reviewers)
    }
    if not active_groups:
        return weights

    # An even split across active domains is the floor for frontend's own share, not just its
    # value at ratio 0 -- this is what makes a fixed-pool phase with no Phase-derived signal at
    # all (frontend_ratio == 0.0, e.g. no linked Phase) reproduce the pre-phase-6 flat
    # even-split-by-count weights exactly, for any mix of active domains, not only the
    # backend-only case (B1's stated example, generalized).
    baseline_share = 1.0 / len(active_groups)
    frontend_share = max(effective_frontend_ratio, baseline_share) if 'frontend' in active_groups else 0.0
    non_frontend_domains = [domain for domain in active_groups if domain != 'frontend']
    remaining_share = 1.0 - frontend_share
    per_non_frontend_domain_share = remaining_share / len(non_frontend_domains) if non_frontend_domains else 0.0

    for domain, members in active_groups.items():
        domain_share = frontend_share if domain == 'frontend' else per_non_frontend_domain_share
        per_member_weight = (domain_pool_size * domain_share) / len(members)
        weights.update({member: per_member_weight for member in members})

    return weights
