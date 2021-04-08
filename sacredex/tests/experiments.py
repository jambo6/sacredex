# import numpy as np
# import pandas as pd
# from sacred import Experiment, Ingredient
#
# from sacredex.artifacts import save_artifact
#
# ex_basic = Experiment("basic")
#
#
# @ex_basic.config
# def basic_config():
#     var1 = 0
#     artifacts = False
#
#
# @ex_basic.main
# def basic_main(_run, var1, artifacts):
#     _run.log_scalar("metric_1", 100)
#
#     # All artifact save formats
#     if artifacts:
#         data = np.random.randn(10, 10)
#         frame = pd.DataFrame(data)
#         save_artifact(_run, data, "data", content_type="np.csv")
#         for content_type in ["pd.csv", "pickle"]:
#             save_artifact(_run, frame, "data", content_type=content_type)
#
#
# EXPERIMENTS = {
#     "basic": {"experiment": ex_basic, "configuration": {"var1": [1, 2]}},
# }
