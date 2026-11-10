const integerFormat = new Intl.NumberFormat('id-ID', {maximumFractionDigits: 0});
const currencyFormat = new Intl.NumberFormat('id-ID', {style: 'currency', currency: 'IDR', maximumFractionDigits: 0});
export const formatInput = value => integerFormat.format(value);
export const formatMoney = value => currencyFormat.format(value);

export function parseRupiah(raw) {
  const text = String(raw).trim();
  if (text.length > 32 || !/^(?:Rp\s*)?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)$/i.test(text)) return null;
  const value = Number(text.replace(/^Rp\s*/i, '').replaceAll('.', ''));
  return Number.isSafeInteger(value) && value >= 0 ? value : null;
}

export function formatEdit(raw, cursor, inputType = '', inserted = null) {
  if (raw === '') return {value: '', caret: 0};
  const digitCount = (raw.slice(0, cursor).match(/[0-9]/g) || []).length;
  let candidate = raw;
  // Typed edits act on the groups we inserted, while pasted amounts are parsed strictly
  const typed = inputType && inputType !== 'insertFromPaste' && inputType !== 'insertFromDrop';
  if (typed && /^[0-9.]+$/.test(raw) && (inserted === null || /^[0-9.]*$/.test(inserted))) {
    candidate = raw.replaceAll('.', '');
  }
  const number = parseRupiah(candidate);
  if (number === null) return {value: raw, caret: cursor};
  const value = formatInput(number);
  let caret = 0, digits = 0;
  while (caret < value.length && digits < digitCount) {
    if (/[0-9]/.test(value[caret])) digits++;
    caret++;
  }
  return {value, caret};
}

export function parseInterestPercent(raw, maximum = 3) {
  const text = String(raw).trim();
  if (!/^[0-9]{1,2}(?:[.,][0-9]{1,2})?$/.test(text)) return null;
  const value = Number(text.replace(',', '.'));
  return value >= 0 && value <= maximum ? value : null;
}

export function installmentFactor(term, rate) {
  return rate === 0 ? 1 / term : rate / -Math.expm1(-term * Math.log1p(rate));
}

export function calculateBudget(values, config) {
  const income = values.ApplicantIncome + values.CoapplicantIncome;
  const term = values.Loan_Amount_Term;
  if (!(income > 0) || !(term > 0)) return null;
  const percent = values.MonthlyInterestPercent ?? config.monthlyRate * 100;
  if (!Number.isFinite(percent) || percent < 0 || percent > (config.maxInterestPercent ?? 3)) return null;
  const factor = installmentFactor(term, percent / 100);
  const payment = values.LoanAmount * factor;
  const reserve = income * config.reserveShare;
  const monthlyBudget = Math.max(0, Math.min(income * config.maxDebtShare - values.ExistingInstallments,
    income - values.LivingExpenses - values.ExistingInstallments - reserve));
  const rawCapacity = monthlyBudget / factor;
  let capacity = Math.min(config.maxLoan, Math.floor(rawCapacity / config.capacityStep) * config.capacityStep);
  if (capacity < config.minLoan) capacity = 0;
  return {income, payment, reserve, monthlyBudget, capacity,
    ratio: (values.ExistingInstallments + payment) / income,
    remaining: income - values.LivingExpenses - values.ExistingInstallments - payment,
    total: payment * term, interest: Math.max(0, payment * term - values.LoanAmount)};
}
