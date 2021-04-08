"""
utils.py
==========================
Contains generic helper functions.
"""
from typing import List

from sklearn.model_selection import ParameterGrid


class DepthError(Exception):
    pass


def nested_parameter_grid(parameter_dict: dict) -> List[dict]:
    """Parameter grid where there can be two nested layers of parameters.

    This is designed to work with sacred ingredients such that our inputs can be structured analogously to the sacred
    configuration file when ingredients have been defined.

    Uses sklearns parameter grid to expand all parameter combinations into a list, allowing for one additional level
    of dictionary.

    Args:
        parameter_dict (dict): A parameter dictionary of the same as for sklearns ParameterGrid, but is now allowed one
            additional level of nesting.

    Example: Suppose we have
        parameter_dict = {
            "seed": [1, 2, 3],
            "dataset": {
                "locations": ["folder1", "folder2"]
            },
            "trainer": {
                "lr": [0.01, 0.1]
            }
    Then application of this function will first convert to labels_split such as "dataset__locations": ["folder1",
    "folder2"] so every item is accessible as a first level key, then runs ParameterGrid, then maps back onto this
    nested dict format.

    Returns:
        A list of dictionaries that equate to all possible combinations, and keeps with the original nesting format.
    """
    if any([isinstance(v, dict) for v in parameter_dict.values()]):
        assert not any(["__" in k for k in parameter_dict.keys()]), (
            "Cannot have __ args as these are used for " "expansion."
        )
        # First make __ keys
        new_parameter_dict = {}
        dunder_keys = []
        for key, value in parameter_dict.items():
            if isinstance(value, dict):
                dunder_keys.append(key)
                for inner_key, inner_value in value.items():
                    if isinstance(inner_value, dict):
                        raise DepthError(
                            "Only allowed one level of inner dictionaries, {} is at depth at least "
                            "2".format(inner_value)
                        )
                    new_parameter_dict[key + "__" + inner_key] = inner_value
            else:
                new_parameter_dict[key] = value

        # Make the grid
        base_parameter_grid = list(ParameterGrid(new_parameter_dict))

        # Put back into the original format
        parameter_grid = []
        for params in base_parameter_grid:
            remapped_params = {key: {} for key in dunder_keys}
            for key, value in params.items():
                if "__" in key:
                    outer_key, inner_key = key.split("__")
                    remapped_params[outer_key][inner_key] = value
                else:
                    remapped_params[key] = value
            parameter_grid.append(remapped_params)
    else:
        parameter_grid = list(ParameterGrid(parameter_dict))

    return parameter_grid
