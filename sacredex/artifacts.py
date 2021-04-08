import logging
import os
import tempfile
from typing import Any, Dict, Union

import mdbh
import numpy as np
import pandas as pd
from bson import ObjectId
from pymongo.database import Database
from sacred.run import Run

from sacredex.save import load_pickle, save_pickle

CONTENT_TYPES = ("np.csv", "pd.csv", "pickle")


def _check_content_type(content_type: str) -> None:
    # Check is in allowed content types
    assert (
        content_type in CONTENT_TYPES
    ), "Allowed content types are {}, got {}.".format(CONTENT_TYPES, content_type)


def save_artifact(
    _run: Run, item: Any, name: str, content_type: str = "pickle"
) -> None:
    """Save an artifact to the run in a format that can be handled by resolve_artifacts on loading.

    This works for the following content_types:
        np.csv: Saves a np.ndarray to a csv file. Will be loaded again with np.loadtxt(fname, delimiter=',')
        pd.csv: Saves a pandas dataframe or series to a csv file. Will be loaded with pd.read_csv(fname, index_col=0)
        pickle: Saves as a pickle, loaded with load_pickle.

    Args:
        _run (sacred.run.Run): The current run object.
        item (np.ndarray, pd.Series, pd.DataFrame, pickleable object): Item to be saved.
        name (str): The identifying name of the data.
        content_type (str): Method of saving, defaults to pickle.

    Returns:
        None
    """
    _check_content_type(content_type)

    # Make a tempfile and dump according to the content type
    fname = tempfile.mkstemp(suffix=".{}".format(content_type))[1]
    if content_type == "np.csv":
        np.savetxt(fname, item, delimiter=",")
    elif content_type == "pd.csv":
        assert any(
            [isinstance(item, x) for x in (pd.DataFrame, pd.Series)]
        ), "pd.csv requires pandas type"
        item.to_csv(fname)
    elif content_type == "pickle":
        save_pickle(item, fname)
    else:
        raise NotImplementedError

    # Save artifact to the run
    _run.add_artifact(fname, name, content_type=content_type)

    # Finally delete the artifact
    os.remove(fname)


def _get_content_type(db: Database, file_id: Union[str, ObjectId]) -> str:
    """ Returns the content type of the specified artifact id. """
    if not isinstance(file_id, ObjectId):
        file_id = ObjectId(file_id)
    return db["fs.files"].find_one({"_id": file_id}, {"contentType": 1})["contentType"]


def _load_artifact(db: Database, id: int, name: str, file_id: str, force=False) -> Any:
    """ Load an artifact specified by its name and id according to its content_type. """
    # mdbh dumps the binary and returns the filename
    fname = mdbh.get_artifact(db, id, name, force)

    # Get the content type so we know how to load
    content_type = _get_content_type(db, file_id=file_id)

    # Load according to the conentent type
    _check_content_type(content_type)
    try:
        if content_type == "np.csv":
            output = np.loadtxt(fname, delimiter=",")
        elif content_type == "pd.csv":
            output = pd.read_csv(fname, index_col=0)
        elif content_type == "pickle":
            output = load_pickle(fname)
        else:
            raise NotImplementedError(
                "Only implemented for content type in {}.".format(CONTENT_TYPES)
            )
    # If fails, continue and let the dict be populated with the exception
    except Exception as output:
        logging.warning(
            "Could not load id:artifact {}:{}, exception {}.".format(id, name, output)
        )

    return output


def resolve_artifacts(db: Database, frame: pd.DataFrame, force=False) -> Dict[str, Any]:
    """Attempt to load every artifact for each dataframe entry.

    This is intended to be used on files that were saved using the `save_artifact` method since the content_type
    save/load methods are synchronised.

    This iterates through the dataframe and the corresponding artifacts attempting to load each artifact into memory.
    The output is a dictionary with ids as keys and each id contains a dictionary of artifact names and loaded values.
    """

    def _resolve_id_artifacts(id, artifacts):
        # Load the artifacts into a named dictionary
        artifact_dict = {}
        for info in artifacts:
            artifact_dict[info["name"]] = _load_artifact(
                db, id, info["name"], info["file_id"], force=force
            )
        return artifact_dict

    artifact_dict = {}
    for id, artifacts in frame["artifacts"].iteritems():
        artifact_dict[id] = _resolve_id_artifacts(id, artifacts)

    return artifact_dict
