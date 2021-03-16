import mdbh


def list_artifacts(db):
    """ List the artifact names. This assumes that all runs contain the same artifacts. """
    print(mdbh.get_artifact_names(db, 2))


def get_artifact(db, run_id, artifact_name, resolve=True):
    """ Gets the specified artifact and attempts a resolution load if set. """
    raise NotImplementedError
