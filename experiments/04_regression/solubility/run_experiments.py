from gptchem.data import get_esol_data, get_solubility_test_data
from loguru import logger

logger.enable("gptchem")
from gptchem.extractor import RegressionExtractor
from gptchem.formatter import RegressionFormatter
from gptchem.tuner import Tuner
from gptchem.querier import Querier
from gptchem.baselines.solubility import train_test_solubility_regression_baseline

from gptchem.evaluator import get_regression_metrics

from pathlib import Path
from fastcore.xtras import save_pickle

num_training_points =  [10, 20, 50, 100, 200, 500]
representations =  ["SMILES", "SELFIES", "InChI"]
num_repeats = 10


def train_test_model(representation, num_train_points, seed):
    train_data = get_esol_data()
    test_data = get_solubility_test_data()

    formatter = RegressionFormatter(
        representation_column=representation,
         property_name="solubility",
        label_column="measured log(solubility:mol/L)",
    )

    train_formatted = formatter(train_data)
    test_formatted = formatter(test_data)

    gpr_baseline = train_test_solubility_regression_baseline(
        train_data,
        test_data,
    )

    tuner = Tuner(n_epochs=8, learning_rate_multiplier=0.02, wandb_sync=False)

    tune_res = tuner(train_formatted)
    querier = Querier(tune_res["model_name"])
    completions = querier(test_formatted)
    extractor = RegressionExtractor()
    extracted = extractor(completions)

    res = get_regression_metrics(test_formatted["label"].values, extracted)

    summary = {
        "representation": representation,
        "num_train_points": num_train_points,
        **res,
        "gpr_baseline": gpr_baseline,
    }

    save_pickle(Path(tune_res["outdir"]) / "summary.pkl", summary)


    print(
        f"Ran train size {num_train_points} and got MAE {res['mean_absolute_error']}, GPR baseline {gpr_baseline['mean_absolute_error']}"
    )



if __name__ == "__main__":
    for seed in range(num_repeats):
        for representation in representations:
            for num_train_points in num_training_points:
                train_test_model(representation, num_train_points, seed + 3657)