from copy import deepcopy

import pytest

from ave_light_renderer.canonical import load_json
from ave_light_renderer.paths import PROJECT_ROOT
from tools.render_four_region_replication import validate_replication


def test_replication_preserves_full_timeline_and_synchronous_policy():
    recipe = load_json(PROJECT_ROOT / 'contracts/examples/vitality-matched-four-region-300s.json')
    validate_replication(recipe)
    intervals = recipe['regions'][0]['intervals']
    assert len(intervals) == 34
    assert intervals[0]['end_us'] == 1_500_000
    assert intervals[-1]['start_us'] == 298_000_000
    assert intervals[1]['phase_policy'] == 'reset'
    assert all(i['phase_policy'] == 'continuous' for i in intervals[2:-1])
    assert min(i['duty_cycle'].get('start', i['duty_cycle'].get('value', 1)) for i in intervals[1:-1]) == 0.01

    divergent = deepcopy(recipe)
    divergent['regions'][1]['intervals'][1]['phase_origin_cycles'] = 0.25
    with pytest.raises(ValueError, match='synchronous'):
        validate_replication(divergent)
