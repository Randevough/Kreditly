"""Reproducible synthetic IDR model for coursework, not Indonesian credit evidence."""
import csv
import json
import pickle
from pathlib import Path

import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix,
                             log_loss, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

from loan_model import ANNUAL_INTEREST, FEATURE_NAMES, TERMS, feature_row, installment

ROOT = Path(__file__).resolve().parent
SEED = 42
SIZE = 20_000


def generate_data(size=SIZE, seed=SEED):
    rng = np.random.default_rng(seed)
    records = []
    for _ in range(size):
        income = float(rng.integers(20, 401) * 100_000)
        co_income = float(rng.integers(0, 151) * 100_000) if rng.random() < .35 else 0.
        combined = income + co_income
        term = int(rng.choice(TERMS))
        existing = float(round(combined * rng.uniform(0, .35) / 10_000) * 10_000)
        expenses = float(round(combined * rng.uniform(.25, .75) / 10_000) * 10_000)
        desired_payment = combined * rng.uniform(.04, .85)
        amount = float(np.clip(round(desired_payment / installment(1, term) / 100_000)
                               * 100_000, 1_000_000, 500_000_000))
        credit = int(rng.choice([0, 1, 2], p=[.2, .6, .2]))
        record = dict(ApplicantIncome=income, CoapplicantIncome=co_income,
                      ExistingInstallments=existing, LivingExpenses=expenses,
                      LoanAmount=amount, Loan_Amount_Term=term, Credit_History=credit)
        features = feature_row(record)
        # Hypothetical label mechanism, not a bank's underwriting policy
        credit_effect = {0: -4., 1: 2., 2: -.5}[credit]
        logit = 4 * (.4 - features[7]) / .15 + 3 * (features[8] / combined - .15) + credit_effect
        probability = 1 / (1 + np.exp(-np.clip(logit, -30, 30)))
        record['Eligible'] = int(rng.random() < probability)
        records.append(record)
    return records


def evaluate(labels, probabilities):
    predictions = probabilities >= .5
    observed, predicted = calibration_curve(labels, probabilities, n_bins=10, strategy='quantile')
    return {
        'accuracy': float(accuracy_score(labels, predictions)),
        'precision': float(precision_score(labels, predictions)),
        'recall': float(recall_score(labels, predictions)),
        'roc_auc': float(roc_auc_score(labels, probabilities)),
        'brier_score': float(brier_score_loss(labels, probabilities)),
        'log_loss': float(log_loss(labels, probabilities)),
        'confusion_matrix': confusion_matrix(labels, predictions).tolist(),
        'calibration_curve': {'mean_probability': predicted.tolist(),
                              'positive_fraction': observed.tolist()},
    }


def main():
    records = generate_data()
    x = np.asarray([feature_row(row) for row in records])
    y = np.asarray([row['Eligible'] for row in records])
    indices = np.arange(len(records))
    train, rest = train_test_split(indices, test_size=.4, random_state=SEED, stratify=y)
    calibration, test = train_test_split(rest, test_size=.5, random_state=SEED, stratify=y[rest])
    estimator = RandomForestClassifier(n_estimators=100, max_depth=9, min_samples_leaf=20,
                                       random_state=SEED, n_jobs=1)
    estimator.fit(x[train], y[train])
    calibrated = CalibratedClassifierCV(FrozenEstimator(estimator), method='sigmoid')
    calibrated.fit(x[calibration], y[calibration])
    metadata = {
        'model_id': 'kreditly-idr-synthetic-v1', 'data_source': 'synthetic',
        'currency': 'IDR', 'seed': SEED, 'sklearn_version': sklearn.__version__,
        'feature_names': FEATURE_NAMES, 'annual_interest_assumption': ANNUAL_INTEREST,
        'decision_threshold': .5,
        'split': {'train': len(train), 'calibration': len(calibration), 'test': len(test)},
        'positive_rate': float(y.mean()),
        'base_test_metrics': evaluate(y[test], estimator.predict_proba(x[test])[:, 1]),
        'calibrated_test_metrics': evaluate(y[test], calibrated.predict_proba(x[test])[:, 1]),
        'limitation': 'All metrics measure agreement with generated hypothetical labels, not real Indonesian lending outcomes',
    }
    artifact = {'model': calibrated, 'metadata': metadata}
    with (ROOT / 'model.pkl').open('wb') as file:
        pickle.dump(artifact, file, protocol=pickle.HIGHEST_PROTOCOL)
    (ROOT / 'model_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    split = {int(i): name for name, ids in [('train', train), ('calibration', calibration),
                                           ('test', test)] for i in ids}
    with (ROOT / 'Dataset' / 'kreditly_synthetic_idr.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[*records[0], 'Split'])
        writer.writeheader()
        writer.writerows(dict(row, Split=split[i]) for i, row in enumerate(records))
    print(json.dumps({key: metadata[key] for key in ['model_id', 'split', 'calibrated_test_metrics']}, indent=2))


if __name__ == '__main__':
    main()
