from copy import deepcopy

import pytest

from ave_light_renderer.canonical import load_json
from ave_light_renderer.paths import SYNTHETIC_RECIPE_PATH


@pytest.fixture
def synthetic_recipe():
    return deepcopy(load_json(SYNTHETIC_RECIPE_PATH))

