from pathlib import Path
import math
import pickle
from flask import Flask, render_template, request

app = Flask(__name__)
# Load only the model bundled by this upstream project.
with (Path(__file__).parent / 'model.pkl').open('rb') as model_file:
    model = pickle.load(model_file)

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html', values=request.form)

@app.post('/predict')
def predict():
    try:
        def number(name, positive=False):
            try:
                value = float(request.form[name])
            except ValueError:
                raise ValueError(name) from None
            if not math.isfinite(value) or value < 0 or (positive and value == 0):
                raise ValueError(name)
            return value
        def choice(name, allowed):
            value = request.form[name]
            if value not in allowed:
                raise ValueError(name)
            return value
        income = number('ApplicantIncome')
        co_income = number('CoapplicantIncome')
        amount = number('LoanAmount', True)
        term = float(choice('Loan_Amount_Term', ['12','36','60','120','180','240','360']))
        credit = float(choice('Credit_History', ['0','1']))
        gender = float(choice('Gender', ['0','1']))
        married = float(choice('Married', ['0','1']))
        dependents = choice('Dependents', ['0','1','2','3+'])
        education = float(choice('Education', ['0','1']))
        employed = float(choice('Self_Employed', ['0','1']))
        area = choice('Property_Area', ['Rural','Semiurban','Urban'])
        # Preserve upstream model's exact 16-feature order and input units.
        features = [income, co_income, amount, term, credit, gender, married,
                    *[float(dependents == n) for n in ['0','1','2','3+']],
                    education, employed,
                    *[float(area == n) for n in ['Rural','Semiurban','Urban']]]
        prediction = model.predict([features])[0]
        return render_template('result.html', approved=bool(prediction == 1),
            amount=f'{amount * 1000:,.0f}', term=int(term), values=request.form)
    except (KeyError, ValueError) as exc:
        field = str(exc.args[0]) if exc.args else ''
        return render_template('index.html', values=request.form, error_field=field,
            error='Ada data yang belum valid. Periksa nominal dan lengkapi semua pilihan, lalu coba lagi.'), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
