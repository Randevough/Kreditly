import assert from 'node:assert/strict';
import test from 'node:test';
import {parseRupiah, formatEdit, formatInput, calculateBudget, parseInterestPercent, installmentFactor} from '../static/money.mjs';
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


test('interest parser accepts decimal comma or dot and rejects invalid rates', () => {
  for (const [raw, expected] of [['0',0],['0,75',.75],['1.50',1.5],['3',3]]) assert.equal(parseInterestPercent(raw), expected);
  for (const raw of ['', '-1', '3.01', '100', 'NaN', 'inf', '1e0', '0.001', '1,2.3', '1%']) assert.equal(parseInterestPercent(raw), null, raw);
});

test('zero interest and custom rates keep costs and capacity consistent', () => {
  const decimal = calculateBudget({...values, MonthlyInterestPercent:.75}, config);
  assert.ok(Math.abs(decimal.payment - 1589986.6329970344) < 1e-6);
  assert.equal(decimal.capacity, 110000000);
  const zero = calculateBudget({...values, MonthlyInterestPercent:0}, config);
  assert.equal(zero.capacity, 126000000);
  assert.ok(Math.abs(zero.payment - values.LoanAmount / 36) < 1e-6);
  assert.ok(Math.abs(zero.interest) < 1e-6);
  for (const term of [6,12,18,24,36,48,60]) {
    let previousPayment = 0, previousCapacity = Infinity;
    for (const percent of [0,.01,.25,.75,1,1.5,2,3]) {
      const result = calculateBudget({...values, Loan_Amount_Term:term, MonthlyInterestPercent:percent}, config);
      assert.ok(result.payment >= previousPayment);
      assert.ok(result.capacity <= previousCapacity);
      assert.ok(result.capacity * installmentFactor(term, percent / 100) <= result.monthlyBudget + 1e-6);
      assert.ok(Math.abs(result.total - result.interest - values.LoanAmount) < 1e-6);
      if (percent === 0) assert.equal(result.interest, 0);
      previousPayment = result.payment;
      previousCapacity = result.capacity;
    }
  }
  for (const percent of [-1,4,NaN,Infinity]) assert.equal(calculateBudget({...values, MonthlyInterestPercent:percent}, config), null);
});
