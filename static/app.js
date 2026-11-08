const form = document.querySelector('#loan-form');
const inputs = [...form.querySelectorAll('input[required], select[required]')];
const submit = form.querySelector('[type="submit"]');
const money = value => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
}).format(value);
const amountValue = name => {
  const value = Number(form.elements.namedItem(name).value);
  return Number.isFinite(value) && value >= 0 ? value : 0;
};
function update() {
  const amount = amountValue('LoanAmount');
  const term = amountValue('Loan_Amount_Term');
  const income = amountValue('ApplicantIncome') + amountValue('CoapplicantIncome');
  document.querySelector('#amount').textContent = Number.isFinite(amount) ? money(amount) : 'Belum diisi';
  document.querySelector('#term').textContent = term ? `${term} bulan` : 'Belum dipilih';
  document.querySelector('#income').textContent = money(income);
  const payment = term && amount ? amount * .01 / (1 - (1.01) ** -term) : 0;
  document.querySelector('#monthly').textContent = payment ? money(payment) : 'Belum dihitung';
  const debt = amountValue('ExistingInstallments');
  const expenses = amountValue('LivingExpenses');
  document.querySelector('#live-ratio').textContent = income && payment ? `${((debt + payment) / income * 100).toLocaleString('id-ID', {maximumFractionDigits: 1})}%` : 'Belum dihitung';
  const remaining = income - expenses - debt - payment;
  document.querySelector('#live-remaining').textContent = income && payment ? money(remaining) : 'Belum dihitung';
  document.querySelector('#live-remaining').classList.toggle('shortfall', remaining < 0);
  const completed = inputs.filter(input => input.value !== '' && input.validity.valid).length;
  document.querySelector('#completion').textContent = `${completed} / ${inputs.length}`;
  document.querySelector('#progress').value = completed;
}
form.addEventListener('input', event => {
  if (event.target.validity.valid) event.target.removeAttribute('aria-invalid');
  update();
});
form.addEventListener('change', update);
const profileButtons = [...document.querySelectorAll('[data-profile]')];
const samples = {
  balanced: { ApplicantIncome: 8000000, CoapplicantIncome: 2000000, LoanAmount: 50000000,
    Loan_Amount_Term: 36, ExistingInstallments: 500000, LivingExpenses: 3500000, Credit_History: 1 },
  tight: { ApplicantIncome: 5000000, CoapplicantIncome: 0, LoanAmount: 100000000,
    Loan_Amount_Term: 36, ExistingInstallments: 1500000, LivingExpenses: 3000000, Credit_History: 1 },
  new: { ApplicantIncome: 6000000, CoapplicantIncome: 0, LoanAmount: 40000000,
    Loan_Amount_Term: 24, ExistingInstallments: 300000, LivingExpenses: 2500000, Credit_History: 2 },
};
profileButtons.forEach(button => button.addEventListener('click', () => {
  Object.entries(samples[button.dataset.profile]).forEach(([name, value]) => {
    form.elements.namedItem(name).value = value;
    form.elements.namedItem(name).removeAttribute('aria-invalid');
  });
  profileButtons.forEach(option => option.setAttribute('aria-pressed', String(option === button)));
  document.querySelector('#error-summary')?.remove();
  update();
}));
form.addEventListener('input', () => profileButtons.forEach(button => button.setAttribute('aria-pressed', 'false')));
form.addEventListener('reset', event => {
  // A native reset would restore server-rendered values after editing a result.
  event.preventDefault();
  profileButtons.forEach(button => button.setAttribute('aria-pressed', 'false'));
  inputs.forEach(input => { input.value = ''; input.removeAttribute('aria-invalid'); });
  document.querySelector('#error-summary')?.remove();
  update();
  inputs[0].focus();
});
form.addEventListener('submit', () => {
  submit.disabled = true;
  submit.querySelector('span').textContent = 'Menghitung hasil';
  form.setAttribute('aria-busy', 'true');
});
window.addEventListener('pageshow', () => {
  submit.disabled = false;
  submit.querySelector('span').textContent = 'Lihat hasil penilaian';
  form.removeAttribute('aria-busy');
  update();
});
update();
document.querySelector('#error-summary')?.focus();
