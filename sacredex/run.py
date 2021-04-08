"""
run.py
===============================
Functions for running experiments over multiple sacred configurations.
"""
import logging
import traceback
from typing import Iterable, Optional, Union

from pymongo import MongoClient
from sacred import Experiment
from sacred.observers import MongoObserver
from tqdm import tqdm


def run_over_configurations(
    ex: Experiment,
    configuration_iterator: Iterable[dict],
    client: Optional[MongoClient] = None,
    db_name: Optional[str] = "sacred",
    purge_first: Optional[bool] = True,
    log_level: Optional[str] = "WARNING",
) -> None:
    """
    Runs a for loop over the specified experiment and configuration iterator.

    Args:
        ex (Experiment): The sacred experiment object.
        configuration_iterator (iterator): An iterator that loops over the configurations.
        client: The pymongo client.
        db_name (str): The name of the database to save to.
        purge_first (bool): Set True to purge runs that do not have the 'COMPLETED' status flag.
        log_level (str): Logging level.

    Returns:
        None
    """
    # Log level and observers
    set_logger(ex, log_level)
    observer = _attach_mongo_observer(ex, client, db_name)

    # Purge if set
    if purge_first:
        purge_incomplete_runs(observer)

    # Loop over configurations
    error_counter = 0
    for i, config in tqdm(
        enumerate(configuration_iterator), desc="Run completion percentage"
    ):
        try:
            run_configuration(ex, config, observer)
        except Exception as e:
            _log_run_error(config, e, error_counter)

    # Note if errors occurred
    print("\nExperiment ran with a total of {} errors".format(error_counter))


def run_configuration(
    ex: Experiment, config: dict, observer: Optional[MongoObserver] = None
) -> None:
    """Run a single configuration dictionary.

    Args:
        ex: Sacred experiment object.
        config (dict): Configuration dictionary with the standard nested ingredient structure.
        observer (MongoObserver): If specified, will check if the config already exists in the observer and skip if
            it does.

    Returns:
        None
    """
    # Ingredients
    top_level_config = _update_ingredient_params(ex, params=config.copy())

    # Skip if run
    if observer is not None:
        if _check_if_run(observer, config):
            return None

    ex.run(config_updates=top_level_config)


def _log_run_error(config: dict, error: str, counter: Optional[int] = 0) -> int:
    """ Print error message for failed run. """
    message = "{}: {}\n Failed for the following configuration: \n{}".format(
        error, traceback.format_exc(), "-" * 50 + "\n" + str(config) + "\n" + "-" * 50
    )
    logging.log(logging.ERROR, message)
    counter += 1
    return counter


def set_logger(ex: Experiment, level: Optional[str] = "WARNING") -> None:
    """ Sets the sacred experiment logger. """
    logger = logging.getLogger("logger")
    logger.setLevel(getattr(logging, level))
    ex.logger = logger


def _delete_run_id(mongo_observer: MongoObserver, run_id: int) -> None:
    """ Deletes the run and metrics given an id. """
    mongo_observer.runs.delete_one({"_id": run_id})
    mongo_observer.metrics.delete_one({"_id": run_id})


def purge_incomplete_runs(mongo_observer: MongoObserver) -> None:
    """ Deletes runs that do not have status marked "COMPLETED" or "RUNNING". """
    # Make sure it has the runs db
    if hasattr(mongo_observer, "runs"):
        incomplete_ids = list(
            mongo_observer.runs.find(
                {"$nor": [{"status": "COMPLETED"}, {"status": "RUNNING"}]}, {"_id": 1}
            )
        )
        for id_dict in incomplete_ids:
            _delete_run_id(mongo_observer, run_id=id_dict["_id"])
        print("Deleted {} failed runs.".format(len(incomplete_ids)))


def _attach_mongo_observer(
    ex: Experiment, client: Union[MongoObserver, None], db_name: str
) -> None:
    """ Attach the observer to the experiment. """
    if client is not None:
        observer = MongoObserver(client=client, db_name=db_name)
        ex.observers.append(observer)
    else:
        logging.log(
            logging.WARNING,
            "No observer has been set. Experiments are not being logged anywhere.",
        )


def _check_if_run(observer: MongoObserver, config: dict) -> bool:
    """Returns True if the configuration is a subset of a configuration that already exists in the database.

    If every entry in the given config dictionary can be found within the configuration of a run in the mongo observer
    then we return True.

    Args:
        observer (MongoObserver): The sacred mongo observer.
        config (dict): Configuration dictionary to be run.

    Returns:
        A boolean denoting whether the configuration has already been run (or at least attempted to be).
    """
    # Create an expression that contains all config elements
    # Query and count the number of documents
    expressions = []
    for key, value in config.items():
        if isinstance(value, dict):
            for inner_key, inner_value in value.items():
                expressions.append({"config.{}.{}".format(key, inner_key): inner_value})
        else:
            expressions.append({"config.{}".format(key): value})
    query = {"$and": expressions}
    count = observer.runs.count_documents(query)

    has_run = True
    if count == 0:
        has_run = False
    elif count > 1:
        logging.log(
            logging.WARNING,
            "Given a config that is a subset of {} existing configs. This may "
            "want checking.".format(count),
        )
    return has_run


def _update_ingredient_params(ex: Experiment, params: dict) -> dict:
    """Updates parameters for sacred ingredients.

    This requires ingredient updates to be the key value pairs in configs such that the key is the ingredient name and
    the value is the configuration dictionary from which to update.
    """
    # Get the names of the ingredients
    ingredients = {i.path: i for i in ex.ingredients}
    ikeys = ingredients.keys()

    # Dictionary keys must correspond to ingredients, we inject this data and remove from the global configs
    for key, value in params.copy().items():
        if isinstance(value, dict):
            assert key in ikeys, (
                "Parameter keys with an associated dict must correspond to a sacred "
                "ingredient. Got key {} and ingredients {}".format(key, ikeys)
            )
            ingredients[key].add_config(**value)
            del params[key]

    return params
