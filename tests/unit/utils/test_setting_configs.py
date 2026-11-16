import pytest
from pydantic import ValidationError

from src.utils.setting_configs import LoopConfig


@pytest.mark.parametrize('variable', ['LOOP_PHASE_LENGTH_SOFT_CAP', 'LOOP_PHASE_SHAPE_SOFT_CAP'])
def test_a_stale_phase_soft_cap_setting_never_breaks_loop_configuration(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    # Phase-cooperative work item 11: the critic no longer scores length, so these settings
    # configure nothing, and a value left in an environment from an older release is ignored.
    monkeypatch.setenv(variable, '1')

    try:
        LoopConfig()
    except ValidationError as error:
        pytest.fail(f'{variable} still configures loop behavior: {error}')
