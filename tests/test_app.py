"""Exercise the real trained artifact, input contract, and application routes."""
import csv
import json
import math
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
import numpy as np

from app import app, metadata, model, parse_rupiah, assessed_capacity
from loan_model import FEATURE_NAMES, feature_row, financials, installment, borrowing_capacity

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

    def test_new_credit_recommendation_survives_the_reported_round_trip(self):
        profile = dict(SAMPLE, ApplicantIncome='6000000', CoapplicantIncome='0',
                       LoanAmount='40000000', Loan_Amount_Term='24', ExistingInstallments='300000',
                       LivingExpenses='2500000', Credit_History='2')
        old_offer = self.client.post('/predict', data=dict(profile, LoanAmount='44600000'))
        self.assertIn('Diprediksi belum memenuhi kelayakan', old_offer.get_data(as_text=True))
        offer = self.client.post('/estimate', data=profile).get_json()
        self.assertEqual(offer['budget_amount'], 44600000)
        self.assertGreater(offer['amount'], 0)
        self.assertLess(offer['amount'], offer['budget_amount'])
        first = self.client.post('/predict', data=profile)
        self.assertIn(f"name=\"LoanAmount\" value=\"{offer['amount']}\"", first.get_data(as_text=True))
        selected = dict(profile, LoanAmount=str(offer['amount']))
        edit = self.client.post('/', data=selected)
        self.assertIn(f"value=\"{offer['amount']}\"", edit.get_data(as_text=True))
        result = self.client.post('/predict', data=selected)
        self.assertIn('Diprediksi memenuhi kelayakan', result.get_data(as_text=True))
        self.assertEqual(self.client.post('/estimate', data=selected).get_json(), offer)

    def test_estimate_validates_input_before_running_model(self):
        for changes in [{'Credit_History': ''}, {'LoanAmount': '-1'}, {'MonthlyInterestPercent': '4'}]:
            with patch.object(model, 'predict_proba', wraps=model.predict_proba) as predict:
                self.assertEqual(self.client.post('/estimate', data=dict(SAMPLE, **changes)).status_code, 400)
                predict.assert_not_called()

    def test_model_rejection_with_budget_room_does_not_offer_a_button(self):
        with patch.object(model, 'predict_proba', side_effect=lambda rows: np.tile([1., 0.], (len(rows), 1))):
            response = self.client.post('/predict', data=SAMPLE)
            self.assertNotIn('Coba nominal ini', response.get_data(as_text=True))
            self.assertIn('Belum ada nominal yang memenuhi penilaian', response.get_data(as_text=True))
            self.assertEqual(self.client.post('/estimate', data=SAMPLE).get_json()['amount'], 0)

    def test_custom_interest_is_used_and_preserved_for_every_plan(self):
        for raw in ['0', '0,75', '1.50', '3']:
            with self.subTest(rate=raw):
                percent = float(raw.replace(',', '.'))
                with patch('app.feature_row', wraps=feature_row) as features:
                    response = self.client.post('/predict', data=dict(SAMPLE, MonthlyInterestPercent=raw))
                self.assertEqual(response.status_code, 200)
                text = response.get_data(as_text=True)
                self.assertIn(f'name="MonthlyInterestPercent" value="{percent}"', text)
                self.assertIn(f"bunga {percent:g}% per bulan".replace('.', ','), text)
                expected = installment(50_000_000, 36, percent / 100)
                self.assertIn(f"Rp{expected:,.0f}".replace(',', '.'), text)
                self.assertGreater(len(features.call_args_list), 1)
                for call in features.call_args_list:
                    self.assertEqual(call.args[0]['MonthlyInterestPercent'], percent)
                edit = self.client.post('/', data=dict(SAMPLE, MonthlyInterestPercent=str(percent)))
                self.assertIn(f'value="{percent}"', edit.get_data(as_text=True))

    def test_invalid_interest_never_reaches_model(self):
        with patch.object(model, 'predict_proba', wraps=model.predict_proba) as predict:
            for raw in ['', '-1', '3.01', '100', 'NaN', 'inf', '1e0', '0.001', '1,2.3', '1%']:
                with self.subTest(rate=raw):
                    response = self.client.post('/predict', data=dict(SAMPLE, MonthlyInterestPercent=raw))
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b'href="#MonthlyInterestPercent"', response.data)
                    self.assertIn(b'value="50000000"', response.data)
            predict.assert_not_called()

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

    def test_formatted_rupiah_matches_plain_amounts(self):
        formatted = dict(SAMPLE, ApplicantIncome='Rp 8.000.000', CoapplicantIncome='2.000.000',
                         LoanAmount='50.000.000', ExistingInstallments='500.000', LivingExpenses='3.500.000')
        response = self.client.post('/predict', data=formatted)
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('Rp1.660.715', text)
        self.assertIn('name="LoanAmount" value="50000000"', text)
        self.assertIn('Rp105.300.000', text)

    def test_ambiguous_currency_is_rejected(self):
        for invalid in ['1.5', '1,5', '-8.000.000', '8.00.000', 'Rp 8.000.000,00', '1e7']:
            with self.subTest(invalid=invalid):
                response = self.client.post('/predict', data=dict(SAMPLE, ApplicantIncome=invalid))
                self.assertEqual(response.status_code, 400)

    def test_costs_are_explicit_and_unknown_fees_are_not_zero(self):
        response = self.client.post('/predict', data=SAMPLE)
        text = response.get_data(as_text=True)
        self.assertIn('Rp9.785.758', text)
        self.assertIn('Rp59.785.758', text)
        self.assertIn('Administrasi dan provisi', text)
        self.assertIn('Belum diperhitungkan', text)
        self.assertIn('biaya hidup', text.lower())

    def test_no_capacity_offer_when_budget_is_exhausted(self):
        response = self.client.post('/predict', data=dict(SAMPLE, LivingExpenses='9000000'))
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('Belum ada nominal yang memenuhi penilaian', text)
        self.assertNotIn('Coba nominal ini', text)
        self.assertIn('Anggaran bulanan belum cukup', text)

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
    def test_offered_amount_fits_budget_and_actual_model_across_profiles_and_rates(self):
        data = {key: float(value) for key, value in SAMPLE.items()}
        for credit in [0, 1, 2]:
            for percent in [0, .75, 1, 1.5, 3]:
                plan = dict(data, Credit_History=credit, MonthlyInterestPercent=percent)
                offer = assessed_capacity(plan)
                self.assertLessEqual(offer['amount'], borrowing_capacity(plan)['amount'])
                if not offer['amount']:
                    continue
                self.assertEqual(offer['amount'] % 100000, 0)
                proposed = dict(plan, LoanAmount=offer['amount'])
                self.assertGreaterEqual(model.predict_proba([feature_row(proposed)])[0][1], metadata['decision_threshold'])
                self.assertLessEqual(financials(proposed)['installment'], offer['monthly_budget'] + 1e-6)
                # The next grid point must exceed the budget or fail the model
                next_amount = offer['amount'] + 100000
                if next_amount <= offer['budget_amount']:
                    self.assertLess(model.predict_proba([feature_row(dict(plan, LoanAmount=next_amount))])[0][1], metadata['decision_threshold'])

    def test_zero_interest_has_no_interest_cost(self):
        data = {key: float(value) for key, value in SAMPLE.items()}
        data['MonthlyInterestPercent'] = 0
        self.assertEqual(installment(12_000_000, 12, 0), 1_000_000)
        self.assertAlmostEqual(financials(data)['installment'] * 36, 50_000_000)
        self.assertEqual(borrowing_capacity(data)['amount'], 126_000_000)

    def test_rate_sweep_preserves_budget_and_model_direction(self):
        data = {key: float(value) for key, value in SAMPLE.items()}
        for term in [6, 12, 18, 24, 36, 48, 60]:
            for credit in [0, 1, 2]:
                previous_payment, previous_capacity, previous_score = 0, math.inf, 1
                for percent in [0, .01, .25, .75, 1, 1.5, 2, 3]:
                    plan = dict(data, Loan_Amount_Term=term, Credit_History=credit, MonthlyInterestPercent=percent)
                    payment = financials(plan)['installment']
                    capacity = borrowing_capacity(plan)
                    score = model.predict_proba([feature_row(plan)])[0][1]
                    self.assertGreaterEqual(payment, previous_payment)
                    self.assertLessEqual(capacity['amount'], previous_capacity)
                    self.assertLessEqual(score, previous_score + 1e-10)
                    self.assertLessEqual(installment(capacity['amount'], term, percent / 100), capacity['monthly_budget'] + 1e-6)
                    # Equal payment at the training rate produces the same model features
                    equivalent = dict(plan, MonthlyInterestPercent=1, LoanAmount=payment / installment(1, term))
                    for actual, expected in zip(feature_row(plan), feature_row(equivalent)):
                        self.assertAlmostEqual(actual, expected, places=12)
                    previous_payment, previous_capacity, previous_score = payment, capacity['amount'], score

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

    def test_capacity_respects_monthly_budget_and_rounds_down(self):
        data = {key: int(value) for key, value in SAMPLE.items()}
        for term in [6, 12, 18, 24, 36, 48, 60]:
            with self.subTest(term=term):
                plan = dict(data, Loan_Amount_Term=term)
                estimate = borrowing_capacity(plan)
                self.assertEqual(estimate['monthly_budget'], 3500000)
                self.assertEqual(estimate['amount'] % 100000, 0)
                self.assertLessEqual(installment(estimate['amount'], term), estimate['monthly_budget'] + .0001)
        self.assertEqual(borrowing_capacity(data)['amount'], 105300000)

    def test_capacity_zero_and_maximum(self):
        data = {key: int(value) for key, value in SAMPLE.items()}
        self.assertEqual(borrowing_capacity(dict(data, LivingExpenses=9000000))['amount'], 0)
        self.assertEqual(borrowing_capacity(dict(data, ExistingInstallments=5000000))['amount'], 0)
        rich = dict(data, ApplicantIncome=40000000, CoapplicantIncome=15000000,
                    ExistingInstallments=0, LivingExpenses=0, Loan_Amount_Term=60)
        self.assertEqual(borrowing_capacity(rich)['amount'], 500000000)
        self.assertTrue(borrowing_capacity(rich)['capped'])

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
