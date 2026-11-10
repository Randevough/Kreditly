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
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from loan_model import ANNUAL_INTEREST, FEATURE_NAMES, TERMS, feature_row, financials, installment

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
        details = financials(record)
        # Hypothetical label mechanism, not a bank's underwriting policy
        credit_effect = {0: -4., 1: 2., 2: -.5}[credit]
        logit = 4 * (.4 - details['debt_ratio']) / .15 + 3 * (details['remaining'] / combined - .15) + credit_effect
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


def write_report(metadata):
    rows = []
    for name, scores in metadata['validation_comparison'].items():
        chosen = 'Dipilih' if name == metadata['selected_model'] else ''
        rows.append(f"| {name} | {scores['accuracy']:.5f} | {scores['brier_score']:.5f} | {scores['log_loss']:.5f} | {chosen} |")
    test = metadata['test_metrics']
    audit = metadata['audit']['metrics']
    report = f"""# Model Card: Kreditly IDR v2

## Tujuan dan asal data

Model penilaian pinjaman pribadi untuk tugas, seluruh nominal menggunakan rupiah
Versi `{metadata['model_id']}` memakai `{metadata['selected_model']}`
Semua 20.000 profil dan label berasal dari generator sintetis seed 42
Tidak ada data peminjam Indonesia nyata atau kebijakan pemberi pinjaman dalam dataset

Label diambil dari distribusi Bernoulli dengan probabilitas logistik hipotetis
Rasio cicilan, sisa penghasilan relatif, dan riwayat kredit membentuk probabilitas generator
Batas acuan 40%, penyangga sisa 15%, dan koefisien pada generator adalah asumsi tugas
Pemilihan fitur mengikuti mekanisme label sintetis yang diketahui, sehingga model linear logistik cocok untuk data ini
Hasil ini tidak membuktikan bahwa hubungan yang sama berlaku di dunia nyata

## Fitur dan konsistensi

| Fitur model | Definisi |
| --- | --- |
| DebtToIncomeRatio | Seluruh cicilan dibagi penghasilan gabungan |
| DisposableIncomeShare | Sisa setelah biaya hidup dan cicilan dibagi penghasilan gabungan |
| CreditArrears | 1 jika pernah menunggak, selain itu 0 |
| CreditHistoryClear | 1 jika riwayat lancar, selain itu 0 |

Riwayat baru diwakili oleh kedua indikator kredit bernilai 0
Penghasilan dan nominal mentah tetap diperlukan untuk menghitung cicilan dan rasio
Gender, pernikahan, pendidikan, dan lokasi tidak digunakan
Pelatihan dan metrik evaluasi memakai bunga 1% per bulan atas saldo berjalan, tanpa biaya lain
Aplikasi mendukung bunga pilihan 0–3% per bulan melalui perhitungan cicilan sebelum ekstraksi fitur
Bunga 0% memakai pokok dibagi tenor, bunga lainnya memakai anuitas dengan cicilan tetap
Model dan metadata tetap memakai artifact awal, belum ada evaluasi akurasi atau kalibrasi khusus untuk bunga lain
Pengujian bunga custom memeriksa konsistensi fitur, arah prediksi, dan batas kemampuan bayar

Arah model diperiksa agar peningkatan pinjaman, cicilan lain, atau biaya hidup tidak meningkatkan skor kelayakan
Peningkatan penghasilan atau tenor tidak menurunkan skor dalam kondisi input lainnya tetap
Saat bunga lebih dari 0%, tenor lebih panjang menambah total pembayaran walaupun cicilan bulanan turun
Pemeriksaan ini adalah kontrak perilaku untuk mekanisme tugas, bukan rekomendasi kebijakan kredit

## Pembagian dan pemilihan model

Train 12.000, calibration 2.000, validation 2.000, test 4.000
Model dasar dilatih pada train saja, calibrator sigmoid memakai calibration saja
Empat kandidat dibandingkan dengan log loss pada validation
Test tidak dipakai untuk memilih kandidat atau ambang klasifikasi
Split test yang sama pernah dipakai mengevaluasi v1 sehingga perbandingan antaversi bersifat berulang
Sesudah pemilihan, audit tambahan memakai 5.000 profil baru dari seed 2026
Audit tidak digunakan untuk memilih atau menyesuaikan model

| Kandidat pada validation | Akurasi | Brier score | Log loss | Pilihan |
| --- | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

## Evaluasi model terpilih

| Metrik | Test 4.000 | Audit 5.000 |
| --- | ---: | ---: |
| Akurasi | {test['accuracy']:.5f} | {audit['accuracy']:.5f} |
| Precision layak | {test['precision']:.5f} | {audit['precision']:.5f} |
| Recall layak | {test['recall']:.5f} | {audit['recall']:.5f} |
| ROC AUC | {test['roc_auc']:.5f} | {audit['roc_auc']:.5f} |
| Brier score | {test['brier_score']:.5f} | {audit['brier_score']:.5f} |
| Log loss | {test['log_loss']:.5f} | {audit['log_loss']:.5f} |

Baseline yang selalu memilih kelas mayoritas mendapat akurasi {metadata['majority_baseline_test_accuracy']*100:.3f}% pada test
Matriks kebingungan test dalam urutan TN, FP, FN, TP: {test['confusion_matrix'][0][0]}, {test['confusion_matrix'][0][1]}, {test['confusion_matrix'][1][0]}, {test['confusion_matrix'][1][1]}
Kurva kalibrasi disimpan dalam metadata, Brier score sendiri bukan ukuran kalibrasi murni
Ambang keputusan tetap 0,5 dan probabilitas tidak ditampilkan sebagai peluang persetujuan nyata

## Batasan dan reproduksi

Semua metrik hanya mengukur kesesuaian pada label hipotetis sintetis
Kalibrasi terhadap label sintetis bukan kalibrasi pada peminjam Indonesia
Indikator keuangan di UI adalah ringkasan input, bukan atribusi sebab akibat dari classifier
Rencana alternatif dihitung ulang memakai model yang sama, perubahan nominal atau tenor tidak menjamin persetujuan
Data observasi berizin dan evaluasi terpisah menurut waktu serta peminjam tetap diperlukan untuk pemakaian nyata

Gunakan Python 3.12 dan versi dependensi pada requirements.txt
Jalankan `python train_model.py` untuk membuat model, dataset, metadata, dan laporan ini
Jalankan `python -m unittest discover -s tests -v` untuk memeriksa aplikasi dan kontrak perilaku

Referensi API: [Logistic Regression](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html), [Random Forest](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestClassifier.html), [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
"""
    (ROOT / 'MODEL_CARD.md').write_text(report, encoding='utf-8')


def main():
    records = generate_data()
    x = np.asarray([feature_row(row) for row in records])
    y = np.asarray([row['Eligible'] for row in records])
    indices = np.arange(len(records))
    train, rest = train_test_split(indices, test_size=.4, random_state=SEED, stratify=y)
    development, test = train_test_split(rest, test_size=.5, random_state=SEED, stratify=y[rest])
    calibration, validation = train_test_split(development, test_size=.5, random_state=SEED,
                                               stratify=y[development])
    estimators = {
        'logistic_regression': make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=2000)),
        'random_forest_monotonic': RandomForestClassifier(
            n_estimators=100, max_depth=9, min_samples_leaf=20, random_state=SEED,
            n_jobs=1, monotonic_cst=[-1, 1, -1, 1]),
    }
    candidates = {}
    for name, estimator in estimators.items():
        estimator.fit(x[train], y[train])
        candidates[name] = estimator
        calibrated = CalibratedClassifierCV(FrozenEstimator(estimator), method='sigmoid')
        calibrated.fit(x[calibration], y[calibration])
        candidates[name + '_sigmoid'] = calibrated
    comparison = {name: evaluate(y[validation], estimator.predict_proba(x[validation])[:, 1])
                  for name, estimator in candidates.items()}
    # Select on validation log loss only, never on final test or audit results
    winner = min(comparison, key=lambda name: comparison[name]['log_loss'])
    selected = candidates[winner]
    test_metrics = evaluate(y[test], selected.predict_proba(x[test])[:, 1])
    # Fresh profiles and labels from another seed, generated after model selection
    audit_records = generate_data(size=5000, seed=2026)
    audit_x = np.asarray([feature_row(row) for row in audit_records])
    audit_y = np.asarray([row['Eligible'] for row in audit_records])
    coefficients = estimators['logistic_regression'].named_steps['logisticregression'].coef_[0]
    if not (coefficients[0] < 0 and coefficients[1] > 0 and coefficients[2] < 0 and coefficients[3] > 0):
        raise RuntimeError('Learned logistic directions do not match the financial contract')
    metadata = {
        'model_id': 'kreditly-idr-synthetic-v2', 'data_source': 'synthetic',
        'currency': 'IDR', 'seed': SEED, 'sklearn_version': sklearn.__version__,
        'feature_names': FEATURE_NAMES, 'annual_interest_assumption': ANNUAL_INTEREST,
        'decision_threshold': .5, 'selected_model': winner,
        'selection_metric': 'validation_log_loss',
        'split': {'train': len(train), 'calibration': len(calibration),
                  'validation': len(validation), 'test': len(test)},
        'positive_rate': float(y.mean()),
        'validation_comparison': comparison,
        'test_metrics': test_metrics,
        'majority_baseline_test_accuracy': float(max(y[test].mean(), 1 - y[test].mean())),
        'audit': {'seed': 2026, 'rows': len(audit_y),
                  'metrics': evaluate(audit_y, selected.predict_proba(audit_x)[:, 1])},
        'monotonic_directions': dict(zip(FEATURE_NAMES, [-1, 1, -1, 1])),
        'limitation': 'All metrics measure agreement with generated hypothetical labels, not real Indonesian lending outcomes',
    }
    with (ROOT / 'model.pkl').open('wb') as file:
        pickle.dump({'model': selected, 'metadata': metadata}, file, protocol=pickle.HIGHEST_PROTOCOL)
    (ROOT / 'model_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    write_report(metadata)
    split = {int(i): name for name, ids in [('train', train), ('calibration', calibration),
                                           ('validation', validation), ('test', test)] for i in ids}
    with (ROOT / 'Dataset' / 'kreditly_synthetic_idr.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[*records[0], 'Split'])
        writer.writeheader()
        writer.writerows(dict(row, Split=split[i]) for i, row in enumerate(records))
    print(json.dumps({'selected_model': winner, 'split': metadata['split'],
                      'test_metrics': test_metrics, 'audit': metadata['audit']}, indent=2))


if __name__ == '__main__':
    main()
