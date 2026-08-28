import pytest

from src.models.enums import CriticAgent
from src.models.phase import Phase
from src.utils.review_weighting import (
    FRONTEND_DOMAIN_POOL_CEILING,
    FRONTEND_DOMAIN_POOL_FLOOR,
    compute_domain_pool_size,
    compute_frontend_ratio,
    compute_phase1_weights,
)

_CORE_WEIGHTS = {
    CriticAgent.AUTOMATED_QUALITY_CHECKER: 25.0,
    CriticAgent.SPEC_ALIGNMENT_REVIEWER: 30.0,
    CriticAgent.CODE_QUALITY_REVIEWER: 20.0,
    CriticAgent.DESIGN_CONFORMANCE_REVIEWER: 20.0,
}


def _phase(skeleton_index: str = '', module_layout: str = '', design_shape_additional: str = '') -> Phase:
    return Phase(
        phase_name='p',
        skeleton_index=skeleton_index or None,
        module_layout=module_layout or None,
        design_shape_additional=design_shape_additional or None,
    )


class TestComputeFrontendRatio:
    def test_no_phase_is_zero(self) -> None:
        assert compute_frontend_ratio(None) == 0.0

    def test_all_backend_paths_is_zero(self) -> None:
        phase = _phase(skeleton_index='- `src/api/routes.py` :: handler() -> None\n')
        assert compute_frontend_ratio(phase) == 0.0

    def test_all_frontend_paths_is_one(self) -> None:
        phase = _phase(skeleton_index='- `src/components/Form.tsx` :: Form() -> JSX.Element\n')
        assert compute_frontend_ratio(phase) == 1.0

    def test_mixed_paths_is_the_frontend_fraction(self) -> None:
        phase = _phase(
            skeleton_index=(
                '- `src/components/Form.tsx` :: Form() -> JSX.Element\n'
                '- `src/api/routes.py` :: handler() -> None\n'
                '- `src/api/models.py` :: User() -> None\n'
                '- `src/api/db.py` :: connect() -> None\n'
            )
        )
        assert compute_frontend_ratio(phase) == 0.25

    def test_module_layout_paths_count_too(self) -> None:
        phase = _phase(module_layout='- `src/components/Form.tsx` — the login form\n')
        assert compute_frontend_ratio(phase) == 1.0

    def test_ux_contract_floors_the_ratio_when_paths_are_backend_only(self) -> None:
        phase = _phase(
            skeleton_index='- `src/api/routes.py` :: handler() -> None\n',
            design_shape_additional='#### UX Contract\n##### Route Index\n',
        )
        assert 0.0 < compute_frontend_ratio(phase) < 1.0

    def test_ux_contract_does_not_lower_an_already_higher_path_based_ratio(self) -> None:
        phase = _phase(
            skeleton_index='- `src/components/Form.tsx` :: Form() -> JSX.Element\n',
            design_shape_additional='#### UX Contract\n##### Route Index\n',
        )
        assert compute_frontend_ratio(phase) == 1.0

    def test_no_paths_and_no_ux_contract_is_zero(self) -> None:
        assert compute_frontend_ratio(_phase()) == 0.0


class TestComputeDomainPoolSize:
    def test_zero_ratio_is_floor(self) -> None:
        assert compute_domain_pool_size(0.0) == FRONTEND_DOMAIN_POOL_FLOOR

    def test_full_ratio_is_ceiling(self) -> None:
        assert compute_domain_pool_size(1.0) == FRONTEND_DOMAIN_POOL_CEILING

    def test_monotonically_increasing_in_ratio(self) -> None:
        # B7
        sizes = [compute_domain_pool_size(r / 10) for r in range(11)]
        assert sizes == sorted(sizes)
        assert len(set(sizes)) == len(sizes)


class TestComputePhase1Weights:
    def test_backend_only_phase_matches_the_pre_phase6_fixed_weights(self) -> None:
        # B1: with no frontend reviewer active, a single active specialist gets the whole
        # floor-sized pool -- byte-for-byte what `15.0 / len(active_specialists)` gave before.
        active = {CriticAgent.AUTOMATED_QUALITY_CHECKER, CriticAgent.BACKEND_API_REVIEWER}
        weights = compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=0.0)

        assert weights[CriticAgent.AUTOMATED_QUALITY_CHECKER] == 25.0
        assert weights[CriticAgent.BACKEND_API_REVIEWER] == 15.0

    def test_no_frontend_ratio_signal_reproduces_flat_even_split_for_any_active_domain_mix(self) -> None:
        # Generalizes B1 beyond the single-specialist case: no design signal at all (e.g. no
        # linked Phase) must reproduce the old flat `pool / count` split regardless of how many
        # domains happen to be active, including frontend.
        active = {
            CriticAgent.AUTOMATED_QUALITY_CHECKER,
            CriticAgent.FRONTEND_REVIEWER,
            CriticAgent.BACKEND_API_REVIEWER,
            CriticAgent.DATABASE_REVIEWER,
            CriticAgent.INFRASTRUCTURE_REVIEWER,
        }
        weights = compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=0.0)

        for reviewer in (
            CriticAgent.FRONTEND_REVIEWER,
            CriticAgent.BACKEND_API_REVIEWER,
            CriticAgent.DATABASE_REVIEWER,
            CriticAgent.INFRASTRUCTURE_REVIEWER,
        ):
            assert weights[reviewer] == FRONTEND_DOMAIN_POOL_FLOOR / 4

    def test_frontend_dominant_phase_raises_the_pool_and_lowers_core_proportionally(self) -> None:
        # B2
        active = {
            CriticAgent.AUTOMATED_QUALITY_CHECKER,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER,
            CriticAgent.CODE_QUALITY_REVIEWER,
            CriticAgent.DESIGN_CONFORMANCE_REVIEWER,
            CriticAgent.FRONTEND_REVIEWER,
        }
        floor_weights = compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=0.0)
        dominant_weights = compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=1.0)

        assert dominant_weights[CriticAgent.FRONTEND_REVIEWER] > floor_weights[CriticAgent.FRONTEND_REVIEWER]
        for core_reviewer in _CORE_WEIGHTS:
            assert dominant_weights[core_reviewer] < floor_weights[core_reviewer]
        # Ratios between core reviewers to each other are preserved under rescaling.
        dominant_ratio = (
            dominant_weights[CriticAgent.SPEC_ALIGNMENT_REVIEWER]
            / dominant_weights[CriticAgent.AUTOMATED_QUALITY_CHECKER]
        )
        floor_ratio = (
            floor_weights[CriticAgent.SPEC_ALIGNMENT_REVIEWER] / floor_weights[CriticAgent.AUTOMATED_QUALITY_CHECKER]
        )
        assert dominant_ratio == pytest.approx(floor_ratio)

    def test_core_reviewers_retain_the_majority_at_the_ceiling(self) -> None:
        # B3
        active = {*_CORE_WEIGHTS, CriticAgent.FRONTEND_REVIEWER}
        weights = compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=1.0)

        core_total = sum(weights[reviewer] for reviewer in _CORE_WEIGHTS)
        pool_total = weights[CriticAgent.FRONTEND_REVIEWER]
        assert core_total > pool_total

    def test_adding_a_second_frontend_domain_reviewer_does_not_change_other_domain_weights(self) -> None:
        # B6
        active_one_frontend = {
            *_CORE_WEIGHTS,
            CriticAgent.FRONTEND_REVIEWER,
            CriticAgent.BACKEND_API_REVIEWER,
            CriticAgent.DATABASE_REVIEWER,
            CriticAgent.INFRASTRUCTURE_REVIEWER,
        }
        weights_one_frontend = compute_phase1_weights(_CORE_WEIGHTS, active_one_frontend, frontend_ratio=0.6)

        # Simulate phase 7 adding a second frontend-domain reviewer by widening the "active"
        # set with a CriticAgent already grouped under 'frontend' in SPECIALIST_DOMAIN_GROUPS.
        import src.utils.review_weighting as review_weighting

        original_groups = review_weighting.SPECIALIST_DOMAIN_GROUPS
        try:
            review_weighting.SPECIALIST_DOMAIN_GROUPS = {
                **original_groups,
                'frontend': frozenset({CriticAgent.FRONTEND_REVIEWER, CriticAgent.CODE_QUALITY_REVIEWER}),
            }
            active_two_frontend = active_one_frontend
            weights_two_frontend = review_weighting.compute_phase1_weights(
                _CORE_WEIGHTS, active_two_frontend, frontend_ratio=0.6
            )
        finally:
            review_weighting.SPECIALIST_DOMAIN_GROUPS = original_groups

        for reviewer in (
            CriticAgent.BACKEND_API_REVIEWER,
            CriticAgent.DATABASE_REVIEWER,
            CriticAgent.INFRASTRUCTURE_REVIEWER,
        ):
            assert weights_two_frontend[reviewer] == weights_one_frontend[reviewer]

    def test_mixed_phase_lands_between_the_bounds_monotonically_in_frontend_share(self) -> None:
        # B7
        active = {*_CORE_WEIGHTS, CriticAgent.FRONTEND_REVIEWER, CriticAgent.BACKEND_API_REVIEWER}
        frontend_weights = [
            compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=r / 10)[CriticAgent.FRONTEND_REVIEWER]
            for r in range(11)
        ]
        assert frontend_weights == sorted(frontend_weights)
        assert frontend_weights[0] < frontend_weights[-1]

    def test_no_active_specialists_leaves_core_weights_unscaled(self) -> None:
        # B5's spirit at the pure-function level: nothing frontend-shaped is active, so the
        # pool stays at the floor and core is untouched -- design-conformance renormalizes
        # away cleanly via the caller's active_weight_total division, not via anything here.
        active = {CriticAgent.AUTOMATED_QUALITY_CHECKER, CriticAgent.SPEC_ALIGNMENT_REVIEWER}
        weights = compute_phase1_weights(_CORE_WEIGHTS, active, frontend_ratio=0.0)

        assert weights == {
            CriticAgent.AUTOMATED_QUALITY_CHECKER: 25.0,
            CriticAgent.SPEC_ALIGNMENT_REVIEWER: 30.0,
        }
