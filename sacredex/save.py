"""
save.py
=============================
Convenience functions for saving and loading.
"""
import json
import pickle
from typing import Any

import json5


def _get_json_func(file: str):
    # Returns json or json5 depending on filename end
    if file.endswith("json"):
        return json
    elif file.endswith("json5"):
        return json5
    else:
        raise NotImplementedError("Filename must end with json or json5")


def load_json(file: str):
    """ Load a json file into a dict. """
    f = _get_json_func(file)
    with open(file) as json_file:
        data = f.load(json_file)
    return data


def save_json(data: dict, fname: str) -> None:
    """ Load a json file into a dict. """
    f = _get_json_func(fname)
    with open(fname, "w") as outfile:
        f.dump(data, outfile)


def save_pickle(obj: Any, filename: str, protocol: int = 4) -> None:
    """Given a python object and a filename, the method will save the object under that filename.

    Args:
        obj (python object): The object to be saved.
        filename (str): Location to save the file.
        protocol (int): Pickling protocol (see pickle docs).

    Returns:
        None
    """
    with open(filename, "wb") as file:
        pickle.dump(obj, file, protocol=protocol)


def load_pickle(filename: str) -> Any:
    """Basic dill/pickle load function.

    Args:
        filename (str): Location of the object.

    Returns:
        The unpickled file.
    """
    with open(filename, "rb") as file:
        obj = pickle.load(file)
    return obj
