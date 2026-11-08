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
if metadata['feature_names'] != FEATURE_NAMES or metadata['currency'] != 'IDR' or metadata['model_id'] != 'kreditly-idr-synthetic-v2':
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
        credit_labels = {0: 'Pernah menunggak', 1: 'Pembayaran lancar', 2: 'Belum punya riwayat'}
        # Compare explicit input changes, not causal explanations of the classifier
        plans = [(data['LoanAmount'], data['Loan_Amount_Term'], 'Rencana saat ini')]
        lower_amount = max(INPUT_LIMITS['LoanAmount'][0], int(data['LoanAmount'] * .8 // 1000) * 1000)
        if lower_amount < data['LoanAmount']:
            plans.append((lower_amount, data['Loan_Amount_Term'], 'Nominal lebih kecil'))
        longer_terms = [term for term in TERMS if term > data['Loan_Amount_Term']]
        plans.extend((data['LoanAmount'], term, f'Tenor {term} bulan') for term in longer_terms[:2])
        comparisons = []
        for amount, term, label in plans:
            plan = dict(data, LoanAmount=amount, Loan_Amount_Term=term)
            plan_details = financials(plan)
            plan_probability = float(model.predict_proba([feature_row(plan)])[0][1])
            comparisons.append({
                'label': label, 'amount': rupiah(amount), 'term': term,
                'installment': rupiah(plan_details['installment']),
                'total': rupiah(plan_details['installment'] * term),
                'approved': plan_probability >= metadata['decision_threshold'],
                'values': {**request.form, 'LoanAmount': str(int(amount)), 'Loan_Amount_Term': str(term)},
            })
        expenses = [data['LivingExpenses'], data['ExistingInstallments'], details['installment'],
                    max(0, details['remaining'])]
        denominator = max(details['income'], sum(expenses))
        shares = [value / denominator * 100 for value in expenses]
        return render_template(
            'result.html', approved=probability >= metadata['decision_threshold'],
            amount=rupiah(data['LoanAmount']), term=data['Loan_Amount_Term'],
            installment=rupiah(details['installment']),
            remaining=rupiah(abs(details['remaining'])), negative_balance=details['remaining'] < 0,
            debt_ratio=f"{details['debt_ratio'] * 100:.1f}".replace('.', ','),
            income=rupiah(details['income']), living=rupiah(data['LivingExpenses']),
            existing=rupiah(data['ExistingInstallments']), credit_label=credit_labels[data['Credit_History']],
            shares=shares, comparisons=comparisons,
            near_boundary=abs(probability - metadata['decision_threshold']) < .1,
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
