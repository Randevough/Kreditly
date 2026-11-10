from pathlib import Path
import pickle
from flask import Flask, render_template, request

from loan_model import (FEATURE_NAMES, INPUT_LIMITS, TERMS, ANNUAL_INTEREST,
                        DEFAULT_INTEREST_PERCENT, MAX_INTEREST_PERCENT,
                        MAX_DEBT_SHARE, RESERVE_SHARE, CAPACITY_STEP,
                        feature_row, financials, borrowing_capacity)
import math
import re

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


@app.context_processor
def calculator_settings():
    return {'calculator_config': {
        'monthlyRate': ANNUAL_INTEREST / 12, 'maxDebtShare': MAX_DEBT_SHARE,
        'reserveShare': RESERVE_SHARE, 'capacityStep': CAPACITY_STEP,
        'minLoan': INPUT_LIMITS['LoanAmount'][0], 'maxLoan': INPUT_LIMITS['LoanAmount'][1],
        'maxInterestPercent': MAX_INTEREST_PERCENT,
    }}


def parse_rupiah(raw, name):
    # Accept whole rupiah or correctly grouped Indonesian amounts, never decimals
    raw = raw.strip()
    if len(raw) > 32 or not re.fullmatch(r'(?:Rp\s*)?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)', raw, re.IGNORECASE):
        raise ValueError(name)
    return int(re.sub(r'^Rp\s*', '', raw, flags=re.IGNORECASE).replace('.', ''))


def parse_interest(raw):
    raw = raw.strip()
    if not re.fullmatch(r'[0-9]{1,2}(?:[.,][0-9]{1,2})?', raw):
        raise ValueError('MonthlyInterestPercent')
    value = float(raw.replace(',', '.'))
    if not 0 <= value <= MAX_INTEREST_PERCENT:
        raise ValueError('MonthlyInterestPercent')
    return value


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html', values=request.form)


@app.post('/predict')
def predict():
    try:
        data = {}
        for name, (minimum, maximum) in INPUT_LIMITS.items():
            try:
                value = parse_rupiah(request.form[name], name)
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
        data['MonthlyInterestPercent'] = parse_interest(request.form.get('MonthlyInterestPercent', str(DEFAULT_INTEREST_PERCENT)))
        details = financials(data)
        values = {name: str(value) for name, value in data.items()}
        capacity = borrowing_capacity(data)
        capacity_values = {**values, 'LoanAmount': str(int(capacity['amount']))}
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
                'saving': rupiah(abs(details['installment'] - plan_details['installment'])),
                'lower_payment': plan_details['installment'] <= details['installment'],
                'approved': plan_probability >= metadata['decision_threshold'],
                'values': {**values, 'LoanAmount': str(int(amount)), 'Loan_Amount_Term': str(term)},
            })
        expenses = [data['LivingExpenses'], data['ExistingInstallments'], details['installment'],
                    max(0, details['remaining'])]
        denominator = max(details['income'], sum(expenses))
        shares = [value / denominator * 100 for value in expenses]
        explanations = []
        if details['remaining'] < 0:
            explanations.append(('Anggaran bulanan belum cukup',
                f"Kebutuhan dan seluruh cicilan melebihi penghasilan sekitar Rp{rupiah(-details['remaining'])} per bulan"))
        else:
            explanations.append(('Masih ada sisa penghasilan',
                f"Setelah kebutuhan dan seluruh cicilan, tersisa sekitar Rp{rupiah(details['remaining'])} per bulan"))
        if details['debt_ratio'] > MAX_DEBT_SHARE:
            explanations.append(('Porsi cicilan cukup besar',
                f"Total cicilan setara {details['debt_ratio'] * 100:.1f}% penghasilan, di atas acuan 40% yang dipakai aplikasi".replace('.', ',')))
        else:
            explanations.append(('Porsi cicilan dalam acuan anggaran',
                f"Total cicilan setara {details['debt_ratio'] * 100:.1f}% penghasilan, masih di dalam acuan 40% aplikasi".replace('.', ',')))
        if data['Credit_History'] == 0:
            explanations.append(('Ada riwayat menunggak', 'Riwayat yang kamu masukkan ikut dipertimbangkan oleh model, kemampuan membayar saja belum menjamin persetujuan'))
        elif probability < metadata['decision_threshold'] and details['remaining'] >= 0 and details['debt_ratio'] <= MAX_DEBT_SHARE:
            explanations.append(('Hasil model masih perlu ditinjau', 'Anggaran yang tersisa bukan satu-satunya masukan model sehingga hasil prediksi bisa berbeda dari perkiraan nominal'))
        return render_template(
            'result.html', approved=probability >= metadata['decision_threshold'],
            amount=rupiah(data['LoanAmount']), term=data['Loan_Amount_Term'],
            interest_percent=f"{data['MonthlyInterestPercent']:g}".replace('.', ','),
            installment=rupiah(details['installment']),
            remaining=rupiah(abs(details['remaining'])), negative_balance=details['remaining'] < 0,
            debt_ratio=f"{details['debt_ratio'] * 100:.1f}".replace('.', ','),
            income=rupiah(details['income']), living=rupiah(data['LivingExpenses']),
            existing=rupiah(data['ExistingInstallments']), credit_label=credit_labels[data['Credit_History']],
            shares=shares, comparisons=comparisons, explanations=explanations,
            capacity_amount=rupiah(capacity['amount']), capacity_available=capacity['amount'] > 0,
            capacity_budget=rupiah(capacity['monthly_budget']), capacity_reserve=rupiah(capacity['reserve']),
            capacity_capped=capacity['capped'], capacity_values=capacity_values,
            total_payment=rupiah(details['installment'] * data['Loan_Amount_Term']),
            total_interest=rupiah(max(0, details['installment'] * data['Loan_Amount_Term'] - data['LoanAmount'])),
            near_boundary=abs(probability - metadata['decision_threshold']) < .1,
            values=values,
        )
    except (KeyError, ValueError) as exc:
        field = str(exc.args[0]) if exc.args else ''
        return render_template(
            'index.html', values=request.form, error_field=field,
            error='Periksa nominal, batas pengisian, dan pilihan yang belum lengkap',
        ), 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
