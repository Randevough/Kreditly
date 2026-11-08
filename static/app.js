import {parseRupiah, formatInput, formatMoney as money, formatEdit, calculateBudget} from './money.mjs';

const form = document.querySelector('#loan-form');
const inputs = [...form.querySelectorAll('input[required], select[required]')];
const moneyInputs = [...form.querySelectorAll('[data-money]')];
const submit = form.querySelector('[type="submit"]');
const config = JSON.parse(document.querySelector('#calculator-config').textContent);
const profileButtons = [...document.querySelectorAll('[data-profile]')];
const capacityButton = document.querySelector('#use-capacity');
let currentCapacity = 0;
const amountValue = name => parseRupiah(form.elements.namedItem(name).value) ?? 0;
const setText = (id, value) => { document.getElementById(id).textContent = value; };

function validateMoney(input, reveal = false) {
  const number = parseRupiah(input.value);
  let message = '';
  if (!input.value.trim()) message = 'Isi kolom ini';
  else if (number === null) message = 'Gunakan rupiah bulat, misalnya 8.000.000';
  else if (number < Number(input.dataset.min) || number > Number(input.dataset.max)) {
    message = `Isi antara ${money(Number(input.dataset.min))} dan ${money(Number(input.dataset.max))}`;
  }
  input.setCustomValidity(message);
  const error = document.getElementById(`${input.name}-error`);
  const show = reveal || input.getAttribute('aria-invalid') === 'true';
  error.textContent = show ? message : '';
  error.hidden = !show || !message;
  if (show && message) input.setAttribute('aria-invalid', 'true');
  else if (!message) input.removeAttribute('aria-invalid');
  return !message;
}

function update() {
  const values = Object.fromEntries(moneyInputs.map(input => [input.name, amountValue(input.name)]));
  values.Loan_Amount_Term = Number(form.elements.namedItem('Loan_Amount_Term').value);
  const amount = values.LoanAmount;
  const term = values.Loan_Amount_Term;
  const income = values.ApplicantIncome + values.CoapplicantIncome;
  const budget = calculateBudget(values, config);
  const payment = term && amount ? amount * config.monthlyRate / (1 - (1 + config.monthlyRate) ** -term) : 0;
  setText('amount', amount ? money(amount) : 'Belum diisi');
  setText('term', term ? `${term} bulan` : 'Pilih tenor');
  setText('income', income ? money(income) : 'Belum diisi');
  setText('monthly', payment ? money(payment) : 'Lengkapi rencana');
  setText('live-total', payment ? money(payment * term) : 'Belum dihitung');
  setText('live-interest', payment ? money(payment * term - amount) : 'Belum dihitung');
  const budgetReady = moneyInputs.filter(input => input.name !== 'LoanAmount')
    .every(input => input.value.trim() !== '' && input.validity.valid) && term > 0;
  setText('live-ratio', budgetReady && payment ? `${(budget.ratio * 100).toLocaleString('id-ID', {maximumFractionDigits: 1})}%` : 'Belum dihitung');
  setText('live-remaining', budgetReady && payment ? money(budget.remaining) : 'Belum dihitung');
  document.querySelector('#live-remaining').classList.toggle('shortfall', !!budget && budget.remaining < 0 && budgetReady);
  currentCapacity = budgetReady ? budget.capacity : 0;
  setText('live-capacity', budgetReady ? (currentCapacity ? money(currentCapacity) : 'Belum ada ruang') : 'Lengkapi anggaranmu');
  setText('capacity-context', budgetReady ? `Untuk tenor ${term} bulan dengan asumsi anggaran aplikasi` : 'Isi penghasilan, pengeluaran, dan tenor untuk melihat perkiraan');
  capacityButton.hidden = !currentCapacity;
  const completed = inputs.filter(input => input.value !== '' && input.validity.valid).length;
  setText('completion', `${completed} dari ${inputs.length} kolom terisi`);
  document.querySelector('#progress').value = completed;
}

moneyInputs.forEach(input => {
  const initial = parseRupiah(input.value);
  if (initial !== null) input.value = formatInput(initial);
  validateMoney(input);
  input.addEventListener('input', event => {
    if (event.isComposing) return;
    const result = formatEdit(input.value, input.selectionStart ?? input.value.length, event.inputType, event.data);
    input.value = result.value;
    input.setSelectionRange(result.caret, result.caret);
    validateMoney(input);
  });
  input.addEventListener('blur', () => validateMoney(input, true));
});
form.addEventListener('invalid', event => {
  if (event.target.matches('[data-money]')) validateMoney(event.target, true);
}, true);
form.addEventListener('input', () => {
  profileButtons.forEach(button => button.setAttribute('aria-pressed', 'false'));
  update();
});
form.addEventListener('change', update);
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
    const input = form.elements.namedItem(name);
    input.value = input.matches('[data-money]') ? formatInput(value) : value;
    input.removeAttribute('aria-invalid');
    if (input.matches('[data-money]')) validateMoney(input);
  });
  profileButtons.forEach(option => option.setAttribute('aria-pressed', String(option === button)));
  document.querySelector('#error-summary')?.remove();
  update();
}));
capacityButton.addEventListener('click', () => {
  if (!currentCapacity) return;
  const input = form.elements.namedItem('LoanAmount');
  input.value = formatInput(currentCapacity);
  validateMoney(input);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.focus();
});
form.addEventListener('reset', event => {
  event.preventDefault();
  profileButtons.forEach(button => button.setAttribute('aria-pressed', 'false'));
  inputs.forEach(input => {
    input.value = '';
    input.removeAttribute('aria-invalid');
    if (input.matches('[data-money]')) validateMoney(input);
  });
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
