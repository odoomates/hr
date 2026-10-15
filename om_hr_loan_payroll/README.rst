===================
HR Loans in Payroll
===================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The bridge between HR Loans and Payroll: the loan installments due come off
the payslips, and are marked repaid when the payslip is confirmed.

Features
========

* A salary rule, Loan Installments (code ``LOAN``, category Deduction), with
  an input of the same code. It deducts the amount of the input, and is left
  out of the payslip when there is nothing to deduct.
* Computing a payslip gives it the installments of the employee's loans being
  repaid that are due by the end of its period and not deducted yet,
  installments of earlier months included, as the ``LOAN`` input. Computed
  again, the input follows the installments.
* The final settlement of an exit (HR Exit in Payroll) deducts every
  installment still due, whatever its month.
* Confirming the payslip marks its installments repaid, on the last day of
  the period, with the payslip as note; the loan is Repaid once all its
  installments are.
* A payslip cancelled or refunded makes its installments due again, and a
  repaid loan goes back to Repaying. A payslip set back to draft keeps its
  installments, to deduct them when confirmed again.
* The installments show the payslip deducting them, on the loan and in
  Employees > Loans > Installments.

Configuration
=============

* The rule is added to the structure "Base for new structures", so the
  structures created from it deduct the loans. The structures that already
  exist are left as they are: add the Loan Installments rule to the ones that
  should deduct the loans, in Payroll > Configuration > Salary Structures.

Usage
=====

#. A loan is approved and paid out in HR Loans.
#. Compute the payslips of the month: the installments due show as the Loan
   Installments line.
#. Confirm the payslips: the installments are repaid.

Dependencies
============

* HR Loans (``om_hr_loan``)
* Payroll (``om_hr_payroll``)

Installs by itself with HR Loans and Payroll.

Support
=======

Odoo Mates, odoomates@gmail.com
