======================
HR Loans in Accounting
======================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The bridge between HR Loans and Accounting: give a loan type a loan account
(receivable) and a payment journal, and its loans are paid out and repaid as
posted payments on that account.

Features
========

* Paid Out registers an outgoing payment to the employee on the loan account,
  dated the day the loan is paid out.
* An installment repaid outside the payroll, or a loan settled at once,
  registers an incoming payment from the employee on it.
* The partner of the payments is the work contact of the employee.
* The loan account is reconciled per employee, so what each employee still
  owes is the balance of their partner on it.
* The Payments button on the loan opens its payments (invoicing users); the
  payment shows the loan it belongs to.
* With the payroll accounting, the installments deducted from the payslips
  credit the loan account too: see HR Loans in Payroll Accounting.

Configuration
=============

* Employees > Configuration > Requests > Loan Types, Accounting section
  (accounting administrators): the Loan Account, a receivable account, and
  the Payment Journal, a bank or cash journal. Both are set per company.
  A loan type without them is not accounted for.

Usage
=====

#. Set the loan account and the payment journal on the loan types.
#. Approve a loan and click Paid Out: the payment to the employee is posted.
#. Mark an installment Repaid, or Settle the loan: the payment from the
   employee is posted and matched with the payout.

Dependencies
============

* HR Loans (``om_hr_loan``)
* Accounting (``account``)

Installs by itself with HR Loans and Accounting.

Support
=======

Odoo Mates, odoomates@gmail.com
