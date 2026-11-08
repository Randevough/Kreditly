const form = document.querySelector('#loan-form');
const inputs = [...form.querySelectorAll('input[required], select[required]')];
const submit = form.querySelector('[type="submit"]');
const money = value => new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', maximumFractionDigits: 0,
}).format(value);
const amountValue = name => {
  const value = Number(form.elements.namedItem(name).value);
  return Number.isFinite(value) && value >= 0 ? value : 0;
};
function update() {
  const amount = amountValue('LoanAmount') * 1000;
  const term = amountValue('Loan_Amount_Term');
  const income = amountValue('ApplicantIncome') + amountValue('CoapplicantIncome');
  document.querySelector('#amount').textContent = Number.isFinite(amount) ? money(amount) : '—';
  document.querySelector('#term').textContent = term ? `${term} bulan` : '—';
  document.querySelector('#income').textContent = money(income);
  document.querySelector('#monthly').textContent = term && amount && Number.isFinite(amount) ? money(amount / term) : '—';
  const completed = inputs.filter(input => input.value !== '' && input.validity.valid).length;
  document.querySelector('#completion').textContent = `${completed} / ${inputs.length}`;
  document.querySelector('#progress').value = completed;
}
form.addEventListener('input', event => {
  if (event.target.validity.valid) event.target.removeAttribute('aria-invalid');
  update();
});
form.addEventListener('change', update);
document.querySelector('#example').addEventListener('click', () => {
  const sample = { ApplicantIncome: 5000, CoapplicantIncome: 1500, LoanAmount: 120,
    Loan_Amount_Term: 360, Credit_History: 1, Self_Employed: 0, Dependents: 1,
    Property_Area: 'Urban', Education: 1, Married: 1, Gender: 1 };
  Object.entries(sample).forEach(([name, value]) => {
    form.elements.namedItem(name).value = value;
    form.elements.namedItem(name).removeAttribute('aria-invalid');
  });
  update();
});
form.addEventListener('reset', event => {
  // A native reset would restore server-rendered values after editing a result.
  event.preventDefault();
  inputs.forEach(input => { input.value = ''; input.removeAttribute('aria-invalid'); });
  document.querySelector('#error-summary')?.remove();
  update();
  inputs[0].focus();
});
form.addEventListener('submit', () => {
  submit.disabled = true;
  submit.querySelector('span').textContent = 'Memproses simulasi…';
  form.setAttribute('aria-busy', 'true');
});
window.addEventListener('pageshow', () => {
  submit.disabled = false;
  submit.querySelector('span').textContent = 'Lihat hasil simulasi';
  form.removeAttribute('aria-busy');
  update();
});
update();
document.querySelector('#error-summary')?.focus();
