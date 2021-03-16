"""
parallel.py
======================================================
Functions for performing runs in parallel.

When performing a run in parallel over multiple python instances (e.g. GNU parallel) we need to keep track of which
experiments have already been run. Ideally I would query the mongo observer to see if the configuration exists, however
in practice the return time is too slow meaning experiments back up against each other and duplicate runs occur.

This file helps keep track of completed runs in such situations.
"""
import os
import random
import tempfile

from .save import load_json, save_json


def dump_config_list_to_json_tmpfiles(config_list):
    """ Saves a list of configuration dictionaries to a temporary folder and returns the folder string. """
    folder = tempfile.mkdtemp()
    for i, c in enumerate(config_list):
        save_json(c, "{}/config_{}.json".format(folder, i))
    return folder


class JsonFolderIterator:
    """Given a list of json files, iterates over the list of jsons and deletes a file once it is loaded.

    This is useful in parallelisation since we need to know which configs have been completed (i.e. the deleted ones).
    I could not implement this functionality more straightforwardly by just checking if a run exists in the mongo db
    since the the for checking took long enough that multiple runs could start for the same config.

    There is still a small chance the config_list could be double loaded, in which case the mongo db needs to be
    amended manually.
    """

    def __init__(self, folder, randomise=True, verbose=1):
        """
        Args:
            folder (str): The folder where the jsons have been saved.
            randomise (bool): Set True to return a random file rather than the next file
            verbose (int): Set as 1 to log the number of files remaining.
        """
        self.folder = folder
        self.randomise = randomise
        self.verbose = 1
        assert all([x.endswith("json") for x in self.files]), "All files must be json."

    @property
    def files(self):
        # Return all files remaining in the folder if exists, else stop
        if self.exists:
            return os.listdir(self.folder)
        else:
            raise StopIteration

    @property
    def exists(self):
        return os.path.isdir(self.folder)

    def next_file(self):
        files = self.files
        if self.randomise:
            file = random.choice(files)
        else:
            file = files[0]
        file = "{}/{}".format(self.folder, file)
        return file

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.files)

    def __next__(self):
        if len(self) > 0:
            # Get the next file
            file = self.next_file()
            config = load_json(file)
            os.remove(file)
            return config
        else:
            if self.exists:
                os.rmdir(self.folder)
            raise StopIteration
