==============================
HR Loans in Payroll Accounting
==============================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The bridge between HR Loans in Accounting, HR Loans in Payroll and Payroll
Accounting: the loan installments deducted from the payslips repay the loan
account of the employee.

Features
========

* The deduction is negative, so the loan account of the loan type is set as
  the debit account of the Loan Installments rule, which credits it; its
  other side is the account the net salary is taken from (the debit account
  of the Net rule). This happens when a loan type is created with a loan
  account, or its loan account changes. Accounts already set on the rule are
  kept.
* The payslip lines on a loan account carry the employee (their work
  contact) as partner, like the payments of the loans.
* The loan account is reconciled per employee once the payslips, or their
  batch, are posted.

Configuration
=============

* Set the loan account on the loan types (HR Loans in Accounting), and the
  accounts of the Net rule (Payroll Accounting). The Loan Installments rule
  is one for all the loan types: it gets the first loan account set and keeps
  it. Check its accounts in Payroll > Configuration > Salary Rules.

Dependencies
============

* HR Loans in Accounting (``om_hr_loan_account``)
* HR Loans in Payroll (``om_hr_loan_payroll``)
* Payroll Accounting (``om_hr_payroll_account``)

Installs by itself with HR Loans in Accounting, HR Loans in Payroll and
Payroll Accounting.

Support
=======

Odoo Mates, odoomates@gmail.com
