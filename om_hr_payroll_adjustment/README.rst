===================
Payroll Adjustments
===================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

What is paid or deducted besides the contract: a bonus, a commission, a fine, a
court deduction, an advance recovered over some months.

Features
========

* **Types** (Payroll > Configuration > Adjustment Types): an addition or a
  deduction, its code and category, the structures paying it, whether it needs
  approval, and whether the final settlement of an employee leaving takes all
  that is still due. Each type has **its own salary rule**, created and kept in
  sync by the type, so the payslips show each kind on its own line. Set the
  accounts of that rule when the payslips are posted in Accounting.
* Six types to start with: Bonus (``ADJ_BONUS``), Commission
  (``ADJ_COMMISSION``), Other Allowance (``ADJ_ALLOWANCE``), Fine
  (``ADJ_FINE``), Court Deduction (``ADJ_COURT``) and Other Deduction
  (``ADJ_DEDUCTION``).
* **Adjustments** (Payroll > Adjustments > Payroll Adjustments): once, monthly
  for a number of months, or monthly until a total; a fixed amount, or a
  percentage of the wage, or of the gross for a deduction (the payslip computes
  again with its gross). An adjustment until a total never goes beyond it.
* **Approval** along the approval flow of the payroll adjustments, by default
  the payroll managers, for the types asking for it (Payroll > Adjustments > To
  Approve).
* **Payslips** take the months due by the end of their period, late ones
  included, and list them on their Adjustments tab; confirming the payslip
  marks them done, cancelling or refunding it makes them due again. A month can
  be postponed, or marked as done outside the payroll, in Payroll > Adjustments
  > Adjustments by Month; an adjustment can be stopped.
* **Add Adjustments** (Payroll > Adjustments > Add Adjustments) gives the same
  adjustment to many employees at once, e.g. a bonus for a department; the
  standard import works too.
* Employees see their running and done adjustments in **My HR > My
  Adjustments**, and on the website portal with *HR Portal: Pay Adjustments*.
* Uninstalling the module removes the salary rules of the types; a rule already
  on payslips is archived to keep their history.

Configuration
=============

* Review the types in Payroll > Configuration > Adjustment Types (payroll
  managers): the structures paying each type, Needs Approval and Settle at
  Exit.
* The approvers are set on the Payroll Adjustments flow in Employees >
  Configuration > Requests > Approval Flows.

Usage
=====

#. Create an adjustment in Payroll > Adjustments > Payroll Adjustments: the
   employee, the type, the recurrence, the amount or the percentage and the
   first month, then click Confirm.
#. When the type needs approval, the approvers approve or refuse it; otherwise
   it runs at once.
#. Compute the payslips: each one takes the months due, on the line of the
   type.

The default types use codes starting with ``ADJ_`` so they never clash with the
rules of a structure.

Dependencies
============

* Odoo 20 HR Payroll (``om_hr_payroll``)
* HR Approvals (``om_hr_approval``)

Support
=======

Odoo Mates, odoomates@gmail.com
