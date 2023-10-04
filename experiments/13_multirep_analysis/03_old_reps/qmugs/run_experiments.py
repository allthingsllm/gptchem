from pathlib import Path

from fastcore.xtras import save_pickle
from sklearn.model_selection import train_test_split

from gptchem.baselines.bandgap import train_test_bandgap_classification_baseline
from gptchem.data import get_qmug_data
from gptchem.evaluator import evaluate_classification
from gptchem.extractor import ClassificationExtractor
from gptchem.formatter import ClassificationFormatter
from gptchem.querier import Querier
from gptchem.tuner import Tuner
import pandas as pd

num_classes = [2, 5]
num_training_points = [10, 50, 100, 200, 500, 1000, 5000]  # 1000
representations = ["tucan", "deepsmiles"]
num_test_points = 250
num_repeats = 10


def train_test_model(num_classes, representation, num_train_points, seed):
    data = pd.read_csv("../../02_multirep/qmugs_data.csv")
    data = data.dropna(subset=[representation, "DFT_HOMO_LUMO_GAP_mean_ev"])
    formatter = ClassificationFormatter(
        representation_column=representation,
        property_name="HOMO-LUMO gap",
        label_column="DFT_HOMO_LUMO_GAP_mean_ev",
        num_classes=num_classes,
    )

    formatted = formatter(data)
    train, test = train_test_split(
        formatted,
        train_size=num_train_points,
        test_size=num_test_points,
        stratify=formatted["label"],
        random_state=seed,
    )

    tuner = Tuner(n_epochs=8, learning_rate_multiplier=0.02, wandb_sync=False)
    tune_res = tuner(train)
    querier = Querier.from_preset(tune_res["model_name"])
    completions = querier(test, logprobs=num_classes)
    extractor = ClassificationExtractor()
    extracted = extractor(completions)

    gpt_metrics = evaluate_classification(test["label"], extracted)

    print(f"Ran train size {num_train_points} and got accuracy {gpt_metrics['accuracy']}")

    summary = {
        **gpt_metrics,
        "train_size": num_train_points,
        "num_classes": num_classes,
        "completions": completions,
        "representation": representation,
        "train_len": len(train),
        "test_len": len(test),
    }

    save_pickle(Path(tune_res["outdir"]) / "summary.pkl", summary)


if __name__ == "__main__":
    for i in range(num_repeats):
        for num_classes in num_classes:
            for num_train_point in num_training_points:
                for representation in representations:
                    try:
                        train_test_model(num_classes, representation, num_train_point, i + 6676)
                    except Exception as e:
                        print(e)
