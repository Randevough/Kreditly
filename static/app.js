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
  document.querySelector('#monthly').textContent = term && amount && Number.isFinite(amount) ? money(amount * .01 / (1 - (1.01) ** -term)) : 'Belum dihitung';
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
  const sample = { ApplicantIncome: 8000000, CoapplicantIncome: 2000000,
    LoanAmount: 50000000, Loan_Amount_Term: 36, ExistingInstallments: 500000,
    LivingExpenses: 3500000, Credit_History: 1 };
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
  submit.querySelector('span').textContent = 'Menghitung hasil';
  form.setAttribute('aria-busy', 'true');
});
window.addEventListener('pageshow', () => {
  submit.disabled = false;
  submit.querySelector('span').textContent = 'Cek kelayakan pinjaman';
  form.removeAttribute('aria-busy');
  update();
});
update();
document.querySelector('#error-summary')?.focus();
