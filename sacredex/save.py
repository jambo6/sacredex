import json
import pickle


def load_json(file):
    """ Load a json file into a dict. """
    with open(file) as json_file:
        data = json.load(json_file)
    return data


def save_json(data, fname):
    """ Load a json file into a dict. """
    with open(fname, "w") as outfile:
        json.dump(data, outfile)


def save_pickle(obj, filename, protocol=4):
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


def load_pickle(filename):
    """Basic dill/pickle load function.

    Args:
        filename (str): Location of the object.

    Returns:
        The unpickled file.
    """
    with open(filename, "rb") as file:
        obj = pickle.load(file)
    return obj
