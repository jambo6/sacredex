import itertools

import pytest

from sacredex.utils import nested_parameter_grid


def _check_lists_have_same_dict_elements(l1, l2):
    # Checks two lists have the same elements when the elements are dictionaries
    assert [x in l2 for x in l1]
    assert [x in l1 for x in l2]


def test_nested_parameter_grid():
    # Check no nesting works as expected (though this is just sklearns param grid)
    no_nesting = {"v1": [1, 2], "v2": [1, 2, 3]}
    param_list = []
    for v1, v2 in zip(
        *[itertools.combinations(no_nesting[x], 1) for x in ("v1", "v2")]
    ):
        param_list.append({"v1": v1, "v2": v2})
    _check_lists_have_same_dict_elements(param_list, nested_parameter_grid(no_nesting))

    # Check nesting works
    nesting = {
        "v1": [1, 2],
        "v2_nest": {
            "v2.1": [3, 4],
        },
    }
    param_list = [
        {"v2_nest": {"v2.1": 3}, "v1": 1},
        {"v2_nest": {"v2.1": 4}, "v1": 1},
        {"v2_nest": {"v2.1": 3}, "v1": 2},
        {"v2_nest": {"v2.1": 4}, "v1": 2},
    ]
    _check_lists_have_same_dict_elements(param_list, nested_parameter_grid(nesting))

    # Error for multiple nests
    triple_nest = {"a": {"b": {"c": [1, 2, 3]}}}
    with pytest.raises(Exception):
        nested_parameter_grid(triple_nest)
