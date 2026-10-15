========
HR Loans
========

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Loans and salary advances for the employees: asked by the employee, approved
along an approval flow, paid out by HR, then repaid in monthly installments.

Features
========

* My HR > My Loans: an employee asks for a loan or a salary advance, with the
  amount, the number of installments, the month of the first installment and
  the reason, then submits it. Compute Installments shows the schedule before
  submitting; submitting computes it otherwise.
* The installments are spread evenly, one a month from the first installment;
  the last one takes what the rounding leaves. A salary advance has a single
  installment.
* Submitting checks the limits of the loan type: maximum amount, maximum
  number of installments, minimum months of service since the first contract,
  an installment at most a share of the wage, and one loan of the type at a
  time.
* The request is approved along the Loans approval flow: the manager of the
  employee, then the HR administrators. Approvers find it under Employees >
  Loans > To Approve, or My HR > To Approve, and approve or refuse it with a
  reason. The Approvals tab of the loan keeps who decided what and when.
* Employees > Loans > All Loans (HR officers): Paid Out marks an approved loan
  as paid to the employee, and its installments become due. HR can still
  cancel an approved loan before it is paid out.
* On the Installments tab, HR postpones an installment, and the ones after it,
  by one month, or marks it repaid outside the payroll. Settle marks
  everything still due as repaid at once, e.g. when the employee repays in
  cash. Once every installment is repaid, the loan is Repaid.
* Employees > Loans > Installments (HR officers): the installments still to
  repay, by month.
* The loan shows what is repaid and what is still due. Draft and cancelled
  loans only can be deleted; the amount and the installments change only
  while the loan is a draft.
* Two loan types come with the module: Salary Advance (one installment, at
  most 50% of the wage) and Personal Loan (up to 12 installments, each at most
  30% of the wage, after 6 months of service).

Configuration
=============

* Employees > Configuration > Requests > Loan Types (HR administrators): the
  name, Salary Advance, Maximum Amount, Maximum Installments, Maximum
  Installment (% of Wage), Minimum Service (Months), One at a Time, the
  company, and a description shown to the employee asking. 0 means no limit.
* Employees > Configuration > Requests > Approval Flows: the Loans flow, its
  steps and their approvers (HR Approvals).

Usage
=====

#. The employee creates a loan in My HR > My Loans and clicks Submit.
#. The manager, then HR, approve it.
#. HR hands over the money and clicks Paid Out.
#. Each month an installment is repaid: deducted from the payslip with HR
   Loans in Payroll, or marked Repaid by HR.

Related modules, installed on their own when their dependencies are:

* HR Loans in Payroll: the installments are deducted from the payslips.
* HR Loans in Accounting: the loans are paid out and repaid as payments on a
  loan account.
* HR Portal: Loans: employees ask for loans and follow them on the website
  portal.

Dependencies
============

* HR Approvals (``om_hr_approval``)

Support
=======

Odoo Mates, odoomates@gmail.com
