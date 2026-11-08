from pathlib import Path
import pickle
from flask import Flask, render_template, request

from loan_model import FEATURE_NAMES, INPUT_LIMITS, TERMS, feature_row, financials
import math

app = Flask(__name__)
# Only load the artifact produced by this repository's train_model.py
with (Path(__file__).parent / 'model.pkl').open('rb') as model_file:
    artifact = pickle.load(model_file)
model = artifact['model']
metadata = artifact['metadata']
if metadata['feature_names'] != FEATURE_NAMES or metadata['currency'] != 'IDR':
    raise RuntimeError('Model input contract does not match the IDR application')


def rupiah(value):
    return f'{value:,.0f}'.replace(',', '.')


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html', values=request.form)


@app.post('/predict')
def predict():
    try:
        data = {}
        for name, (minimum, maximum) in INPUT_LIMITS.items():
            try:
                value = float(request.form[name])
            except ValueError:
                raise ValueError(name) from None
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError(name)
            data[name] = value
        for name, allowed in [('Loan_Amount_Term', TERMS), ('Credit_History', (0, 1, 2))]:
            value = request.form[name]
            if value not in [str(option) for option in allowed]:
                raise ValueError(name)
            data[name] = int(value)
        details = financials(data)
        probability = float(model.predict_proba([feature_row(data)])[0][1])
        return render_template(
            'result.html', approved=probability >= metadata['decision_threshold'],
            amount=rupiah(data['LoanAmount']), term=data['Loan_Amount_Term'],
            installment=rupiah(details['installment']),
            remaining=rupiah(details['remaining']),
            debt_ratio=f"{details['debt_ratio'] * 100:.1f}".replace('.', ','),
            values=request.form,
        )
    except (KeyError, ValueError) as exc:
        field = str(exc.args[0]) if exc.args else ''
        return render_template(
            'index.html', values=request.form, error_field=field,
            error='Periksa nominal, batas pengisian, dan pilihan yang belum lengkap',
        ), 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
