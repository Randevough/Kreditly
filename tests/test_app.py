"""Exercise the real trained artifact, input contract, and application routes."""
import csv
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from app import app, metadata, model
from loan_model import FEATURE_NAMES, feature_row, financials, installment

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = {
    'ApplicantIncome': '8000000', 'CoapplicantIncome': '2000000',
    'LoanAmount': '50000000', 'Loan_Amount_Term': '36',
    'ExistingInstallments': '500000', 'LivingExpenses': '3500000',
    'Credit_History': '1',
}


class CopyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.copy = []
        self.hidden = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = False

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.copy.append(data.strip())


class FormTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_has_local_financial_fields(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for name in SAMPLE:
            self.assertIn(f'name="{name}"', response.get_data(as_text=True))
        for removed in ['Gender', 'Married', 'Education', 'Property_Area']:
            self.assertNotIn(f'name="{removed}"', response.get_data(as_text=True))

    def test_real_model_positive_prediction(self):
        response = self.client.post('/predict', data=SAMPLE)
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('Diprediksi memenuhi kelayakan', text)
        self.assertIn('Rp50.000.000', text)
        self.assertIn('21,6%', text)
        self.assertIn('name="ApplicantIncome" value="8000000"', text)

    def test_real_model_negative_prediction(self):
        data = dict(SAMPLE, ApplicantIncome='2000000', CoapplicantIncome='0',
                    LoanAmount='100000000', ExistingInstallments='1000000',
                    LivingExpenses='1800000', Credit_History='0')
        response = self.client.post('/predict', data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Diprediksi belum memenuhi kelayakan', response.get_data(as_text=True))

    def test_invalid_values_skip_prediction_and_preserve_form(self):
        with patch.object(model, 'predict_proba', wraps=model.predict_proba) as predict:
            for invalid in ['-1', 'nan', 'inf', 'bad', '', '0', '1e300', '40000001']:
                with self.subTest(invalid=invalid):
                    response = self.client.post('/predict', data=dict(SAMPLE, ApplicantIncome=invalid))
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b'value="50000000"', response.data)
                    self.assertIn(b'href="#ApplicantIncome"', response.data)
            predict.assert_not_called()

    def test_bounds_and_choices(self):
        for field, invalid in [('LoanAmount', '999999'), ('LoanAmount', '500000001'),
                               ('CoapplicantIncome', '15000001'),
                               ('ExistingInstallments', '-1'), ('LivingExpenses', 'inf'),
                               ('Loan_Amount_Term', '360'), ('Credit_History', '3')]:
            with self.subTest(field=field, invalid=invalid):
                self.assertEqual(self.client.post('/predict', data=dict(SAMPLE, **{field: invalid})).status_code, 400)

    def test_missing_field(self):
        data = SAMPLE.copy()
        del data['Credit_History']
        response = self.client.post('/predict', data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'href="#Credit_History"', response.data)

    def test_new_credit_history_is_supported(self):
        response = self.client.post('/predict', data=dict(SAMPLE, Credit_History='2'))
        self.assertEqual(response.status_code, 200)

    def test_edit_escapes_input_and_keeps_values(self):
        response = self.client.post('/', data=dict(SAMPLE, ApplicantIncome='"><script>alert(1)</script>'))
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert(1)</script>', response.data)
        self.assertIn(b'value="50000000"', response.data)

    def test_plan_comparison_reuses_model_and_inputs(self):
        response = self.client.post('/predict', data=SAMPLE)
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('Nominal lebih kecil', text)
        self.assertIn('Rp40.000.000', text)
        self.assertIn('Tenor 48 bulan', text)
        self.assertIn('name="LivingExpenses" value="3500000"', text)
        self.assertIn('Total pembayaran', text)
        self.assertIn('Rp1.660.715', text)

    def test_minimum_amount_maximum_term_has_no_duplicate_plans(self):
        response = self.client.post('/predict', data=dict(SAMPLE, LoanAmount='1000000', Loan_Amount_Term='60'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Nominal lebih kecil', response.get_data(as_text=True))
        self.assertIn('1 rencana', response.get_data(as_text=True))

    def test_overspending_result_reports_shortfall(self):
        response = self.client.post('/predict', data=dict(SAMPLE, LivingExpenses='20000000'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('melebihi penghasilan', response.get_data(as_text=True))
        self.assertIn('-Rp', response.get_data(as_text=True))
        self.assertNotIn('Rp-', response.get_data(as_text=True))

    def test_copy_has_no_dollar_simulation_or_ending_dots(self):
        for response in [self.client.get('/'), self.client.post('/predict', data=SAMPLE),
                         self.client.post('/predict', data=dict(SAMPLE, LoanAmount='-1'))]:
            parser = CopyParser()
            parser.feed(response.get_data(as_text=True))
            for text in parser.copy:
                self.assertFalse(text.endswith('.'), text)
                for removed in ['$', '—', 'simulasi', 'USD']:
                    self.assertNotIn(removed, text)
            self.assertIn('Rp', ' '.join(parser.copy))


class ModelTests(unittest.TestCase):
    def test_financial_calculation(self):
        data = {key: float(value) for key, value in SAMPLE.items()}
        details = financials(data)
        self.assertAlmostEqual(installment(50_000_000, 36), 1_660_715.4906425588, places=2)
        self.assertAlmostEqual(details['debt_ratio'], .21607154906425588)
        self.assertAlmostEqual(details['remaining'], 4_339_284.509357441, places=2)
        features = feature_row(data)
        self.assertAlmostEqual(features[0], details['debt_ratio'])
        self.assertAlmostEqual(features[1], details['remaining'] / details['income'])
        self.assertEqual(features[2:], [0., 1.])
        self.assertEqual(len(features), len(FEATURE_NAMES))

    def test_financial_directions_are_consistent(self):
        data = {key: float(value) for key, value in SAMPLE.items()}
        def score(**changes):
            return model.predict_proba([feature_row(dict(data, **changes))])[0][1]
        # These are behavioral contracts, not accuracy claims about real borrowers
        for field, values, increasing in [
            ('LoanAmount', [10_000_000, 25_000_000, 50_000_000, 100_000_000, 200_000_000], False),
            ('ExistingInstallments', [0, 500_000, 1_500_000, 3_000_000], False),
            ('LivingExpenses', [1_000_000, 3_000_000, 5_000_000, 8_000_000], False),
            ('ApplicantIncome', [2_000_000, 5_000_000, 8_000_000, 15_000_000, 30_000_000], True),
            ('Loan_Amount_Term', [6, 12, 24, 36, 48, 60], True),
        ]:
            with self.subTest(field=field):
                scores = [score(**{field: value}) for value in values]
                for before, after in zip(scores, scores[1:]):
                    self.assertGreaterEqual(after + 1e-10, before) if increasing else self.assertLessEqual(after, before + 1e-10)
        self.assertLessEqual(score(Credit_History=0), score(Credit_History=2))
        self.assertLessEqual(score(Credit_History=2), score(Credit_History=1))

    def test_selected_on_validation_not_test(self):
        rows = metadata['validation_comparison']
        self.assertEqual(metadata['selected_model'], min(rows, key=lambda name: rows[name]['log_loss']))
        self.assertEqual(metadata['split'], {'train': 12000, 'calibration': 2000, 'validation': 2000, 'test': 4000})
        self.assertEqual(metadata['audit']['rows'], 5000)
        self.assertNotEqual(metadata['audit']['seed'], metadata['seed'])

    def test_artifact_contract_and_provenance(self):
        self.assertEqual(metadata['currency'], 'IDR')
        self.assertEqual(metadata['data_source'], 'synthetic')
        self.assertEqual(metadata['feature_names'], FEATURE_NAMES)
        self.assertEqual(model.n_features_in_, len(FEATURE_NAMES))
        self.assertEqual(metadata, json.loads((ROOT / 'model_metadata.json').read_text()))

    def test_dataset_split_and_no_repeated_profiles(self):
        with (ROOT / 'Dataset/kreditly_synthetic_idr.csv').open() as file:
            records = list(csv.DictReader(file))
        seen = set()
        for name, count in metadata['split'].items():
            group = [row for row in records if row['Split'] == name]
            self.assertEqual(len(group), count)
            for row in group:
                profile = tuple(row[key] for key in SAMPLE)
                self.assertNotIn(profile, seen)
                seen.add(profile)


if __name__ == '__main__':
    unittest.main()
