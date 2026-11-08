import assert from 'node:assert/strict';
import test from 'node:test';
import {parseRupiah, formatEdit, formatInput, calculateBudget} from '../static/money.mjs';
const config = {monthlyRate:.01, maxDebtShare:.4, reserveShare:.15, capacityStep:100000, minLoan:1000000, maxLoan:500000000};
const values = {ApplicantIncome:8000000, CoapplicantIncome:2000000, LoanAmount:50000000, Loan_Amount_Term:36, ExistingInstallments:500000, LivingExpenses:3500000};
test('whole rupiah accepts plain, grouped, and prefixed amounts', () => {
  for (const raw of ['8000000', '8.000.000', 'Rp 8.000.000', 'Rp\u00a08.000.000', '0008000000']) assert.equal(parseRupiah(raw), 8000000);
  assert.equal(parseRupiah('0'), 0);
});
test('ambiguous, negative, and malformed pasted amounts stay invalid', () => {
  for (const raw of ['', '-8.000.000', '1.5', '1,5', '8.00.000', '8e6', 'uang8000', 'NaN', 'Infinity', '8.000.000,00']) assert.equal(parseRupiah(raw), null, raw);
  assert.equal(formatEdit('-8000',5,'insertFromPaste').value, '-8000');
  assert.equal(formatEdit('1.5',3,'insertFromPaste').value, '1.5');
});
test('typing, middle edits, deletion and cursor placement preserve digits', () => {
  assert.deepEqual(formatEdit('8000000',7,'insertText','0'), {value:'8.000.000',caret:9});
  assert.deepEqual(formatEdit('8.000.00',8,'deleteContentBackward'), {value:'800.000',caret:7});
  assert.deepEqual(formatEdit('85.000.000',2,'insertText','5'), {value:'85.000.000',caret:2});
  assert.equal(formatEdit('Rp 8.000.000',12,'insertFromPaste').value, '8.000.000');
  assert.equal(formatInput(50000000), '50.000.000');
});
test('budget estimate matches the server example and cost identity', () => {
  const result = calculateBudget(values, config);
  assert.equal(result.capacity, 105300000);
  assert.equal(result.monthlyBudget, 3500000);
  assert.ok(Math.abs(result.payment - 1660715.4906425588) < .001);
  assert.ok(Math.abs(result.total - result.interest - values.LoanAmount) < .001);
});
test('capacity respects reserve, current debts, lower bound, and application cap', () => {
  assert.equal(calculateBudget({...values, LivingExpenses:9000000}, config).capacity, 0);
  assert.equal(calculateBudget({...values, ExistingInstallments:5000000}, config).capacity, 0);
  assert.equal(calculateBudget({...values, ApplicantIncome:40000000, CoapplicantIncome:15000000, LivingExpenses:0, ExistingInstallments:0, Loan_Amount_Term:60}, config).capacity, 500000000);
  assert.equal(calculateBudget({...values, ApplicantIncome:0, CoapplicantIncome:0}, config), null);
});
