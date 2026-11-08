"""Financial inputs and assumptions shared by training and serving."""
import math

ANNUAL_INTEREST = 0.12  # Assignment assumption, not a lender offer
TERMS = (6, 12, 18, 24, 36, 48, 60)
INPUT_LIMITS = {
    'ApplicantIncome': (2_000_000, 40_000_000),
    'CoapplicantIncome': (0, 15_000_000),
    'ExistingInstallments': (0, 20_000_000),
    'LivingExpenses': (0, 40_000_000),
    'LoanAmount': (1_000_000, 500_000_000),
}
FEATURE_NAMES = [
    'DebtToIncomeRatio', 'DisposableIncomeShare', 'CreditArrears', 'CreditHistoryClear',
]


def installment(amount, term):
    rate = ANNUAL_INTEREST / 12
    return amount * rate / (1 - (1 + rate) ** -term)


def financials(data):
    income = data['ApplicantIncome'] + data['CoapplicantIncome']
    if not math.isfinite(income) or income <= 0:
        raise ValueError('ApplicantIncome')
    payment = installment(data['LoanAmount'], data['Loan_Amount_Term'])
    debt_ratio = (data['ExistingInstallments'] + payment) / income
    remaining = income - data['LivingExpenses'] - data['ExistingInstallments'] - payment
    return {'income': income, 'installment': payment,
            'debt_ratio': debt_ratio, 'remaining': remaining}


def feature_row(data):
    details = financials(data)
    # Ratios make identical financial burdens comparable across income levels
    return [details['debt_ratio'], details['remaining'] / details['income'],
            float(data['Credit_History'] == 0), float(data['Credit_History'] == 1)]
