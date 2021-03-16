import warnings

import mdbh
import pandas as pd


def _get_prefixed_elements(lst, prefix):
    """ Get elements from a list of strings that begin with a specified prefix. """
    return [x for x in lst if x.startswith(prefix)]


def _convert_dict_elements(frame, columns):
    """Conversion methods for columns in a seed_averaged_frame that contain dictionary type entries.

    Sacred converts tuples to dicts to work with json format. Here we expand back out into tuples to provide a more
    natural format, as well as to enable the use of aggregation funtions.

    Implemented methods:
        - Conversion of list to tuple (since lists cannot be aggregated)
        - Conversion of 'py/tuple' dict to tuple
    """
    for col in columns:
        entry = frame.iloc[0][col]
        if isinstance(entry, list):
            frame[col] = frame[col].apply(lambda x: tuple(x))
        if isinstance(entry, dict):
            if all([len(entry) == 1, isinstance(entry.get("py/tuple"), list)]):
                frame[col] = frame[col].apply(lambda x: tuple(x["py/tuple"]))
            else:
                warnings.warn(
                    "Dict entry for column {} is not a py/tuple dict, do not know how to handle the entry "
                    "and so it is being left as it is. This will prevent aggregation functions from working."
                )
    return frame


def get_dataframe(
    db,
    ids=None,
    completed_only=True,
    include_artifacts=True,
    open_metrics=True,
    cache=False,
):
    """Adds small functionality to mdbh.get_dataframe.

    Args:
        db (mongo database): The mongo database containing the runs and
        ids (list): List of ids to be queries for. Leave as None for all ids.
        completed_only (bool): Set True to return 'COMPLETED' runs only.
        include_artifacts (bool): Set True to return artifact list.
        open_metrics (bool): Set True to open metrics of length 1 from list -> value.
        average_seeds (bool): Set True to average the metrics (keeping hold of the stddevs) over the seeds. This creates
            two new metrics 'metrics.metric_name.mean', 'metrics.metric_name.std'. Note, this cannot be performed if
            open metrics is not set to True. Further note, this will concatenate the id column into a new feature and
            drop everything but the config and metric information since it is not clear how to handle the mean
            operation.
        cache (bool): See mdbh.get_dataframe.

    Returns:
        A pandas dataframe containing all information.
    """
    frame = mdbh.get_dataframe(
        db, ids, include_artifacts=include_artifacts, cache=cache
    )

    if completed_only:
        frame = frame[frame["status"] == "COMPLETED"]

    # Col types
    config_cols = _get_prefixed_elements(frame.columns, "config.")
    metric_cols = _get_prefixed_elements(frame.columns, "metrics.")

    # Expand tuple dicts to tuples
    frame = _convert_dict_elements(frame, config_cols)

    # Single valued metrics are still returned as a list so we open them to their singular value
    if open_metrics:

        def metric_opener(x):
            if len(x) == 1:
                x = x[0]
            return x

        for col in metric_cols:
            frame[col] = frame[col].apply(metric_opener)

    return frame


def average_metrics_over_seed(frame, string_rounding=3, string_scaling=1.0):
    """Average metrics over different seeds for grouped config_list.

    Computes the mean and standard deviation of all metrics for each group of config_list with different seed values.
    Returns a new dataframe with [metric_name.mean, metric_name.std, metric_name.latex_str] columns and the grouped
    config_list as the index.

    Args:
        frame (DataFrame): Dataframe that will usually be the output of sacredex.get_dataframe
        string_rounding (int): Value to round the mean and std to when generating the string representation.
        string_scaling (float): Multiplies the mean and std by this value before producing the string representation.
            This will usually be either 1 (for no scaling) or 100 (when wanting to scale to 100%).

    Todo:
        - Handle situations where some metrics are list valued
    """
    # Col names
    metric_cols = [x for x in frame.columns if x.startswith("metrics.")]
    config_cols = [
        x for x in frame.columns if x.startswith("config.") if x != "config.seed"
    ]

    # Group features, get mean std, create new seed_averaged_frame
    group = frame.groupby(config_cols)[metric_cols]
    mean, std = group.mean(), group.std()
    seed_averaged_frame = pd.concat([mean, std], axis=1)
    seed_averaged_frame.columns = [
        "{}.{}".format(x, y) for y in ("mean", "std") for x in metric_cols
    ]

    # Create some string representations
    for metric_name in metric_cols:
        mean_str, std_str = [
            (seed_averaged_frame["{}.{}".format(metric_name, x)] * string_scaling)
            .round(string_rounding)
            .apply(str)
            for x in ("mean", "std")
        ]
        seed_averaged_frame["{}.latex_string".format(metric_name)] = (
            mean_str + " /pm " + std_str
        )

    # Finally add the run ids that these runs came from
    ids = frame.groupby(config_cols)["id"].apply(lambda x: list(x.values.reshape(-1)))
    seed_averaged_frame["run_ids"] = ids

    return seed_averaged_frame
