"""Route checks isolate form behavior from the version-sensitive pickle model."""
import unittest
from unittest.mock import Mock, patch

with patch('pickle.load', return_value=Mock()) as loader:
    from app import app, model

SAMPLE = {
    'ApplicantIncome': '5000', 'CoapplicantIncome': '1500', 'LoanAmount': '120',
    'Loan_Amount_Term': '360', 'Credit_History': '1', 'Gender': '1',
    'Married': '1', 'Dependents': '1', 'Education': '1',
    'Self_Employed': '0', 'Property_Area': 'Urban',
}


class FormTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        model.reset_mock()
        model.predict.return_value = [1]

    def test_home(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'loan-form', response.data)
        self.assertNotIn(b'aria-invalid="true"', response.data)

    def test_feature_order_and_result(self):
        response = self.client.post('/predict', data=SAMPLE)
        self.assertEqual(response.status_code, 200)
        model.predict.assert_called_once_with([[5000., 1500., 120., 360., 1., 1., 1.,
                                               0., 1., 0., 0., 1., 0., 0., 0., 1.]])
        text = response.get_data(as_text=True)
        self.assertIn('Diprediksi memenuhi kelayakan.', text)
        self.assertIn('US$120,000', text)
        self.assertIn('name="ApplicantIncome" value="5000"', text)

    def test_negative_prediction(self):
        model.predict.return_value = [0]
        response = self.client.post('/predict', data=SAMPLE)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Diprediksi belum memenuhi kelayakan.', response.get_data(as_text=True))

    def test_invalid_numbers_preserve_values_and_skip_model(self):
        for invalid in ['-1', 'nan', 'inf', 'bad', '']:
            with self.subTest(invalid=invalid):
                data = dict(SAMPLE, ApplicantIncome=invalid)
                response = self.client.post('/predict', data=data)
                self.assertEqual(response.status_code, 400)
                text = response.get_data(as_text=True)
                self.assertIn('value="120"', text)
                self.assertIn('value="Urban" selected', text)
                self.assertIn('href="#ApplicantIncome"', text)
                self.assertIn('aria-invalid="true"', text)
        model.predict.assert_not_called()

    def test_choices_and_amount_validation(self):
        for field, value in [('LoanAmount', '0'), ('Loan_Amount_Term', '2'),
                             ('Credit_History', 'yes'), ('Dependents', '4'),
                             ('Property_Area', 'unknown')]:
            with self.subTest(field=field):
                response = self.client.post('/predict', data=dict(SAMPLE, **{field: value}))
                self.assertEqual(response.status_code, 400)
        model.predict.assert_not_called()

    def test_missing_field(self):
        data = SAMPLE.copy()
        del data['Gender']
        response = self.client.post('/predict', data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'href="#Gender"', response.data)
        model.predict.assert_not_called()

    def test_edit_keeps_form_and_escapes_values(self):
        response = self.client.post('/', data=dict(SAMPLE, ApplicantIncome='"><script>alert(1)</script>'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert(1)</script>', response.data)
        self.assertIn(b'value="Urban" selected', response.data)
        model.predict.assert_not_called()


if __name__ == '__main__':
    unittest.main()
