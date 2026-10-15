===========================
Shift Allowances in Payroll
===========================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Bridge between Shifts and Payroll: pays on the payslips the allowance of each
published shift, e.g. a night shift allowance.

Features
========

* The allowance is set per shift template (Shifts > Configuration > Shift
  Templates > *Allowance per Shift*).
* When a payslip is computed, the published shifts of the employee up to the end
  of its period, not paid yet, give the input ``SHIFT_ALW``, paid by the *Shift
  Allowances* salary rule (category Allowance).
* A shift on time off or a public holiday for its whole time is not paid.
* Each shift is paid once: it is linked to the payslip paying it, and becomes
  payable again if that payslip is cancelled or refunded. A shift published
  after its payslip is paid on the next one.
* The *Shift Allowances* tab of the payslip lists the shifts it pays; the shift
  form shows the allowance and, for the payroll officers, the payslip that paid
  it.
* The base salary structure gets the rule, so the structures created from it
  pay the allowances.

Configuration
=============

* Set an allowance on the shift templates that pay one.
* Add the *Shift Allowances* rule (``SHIFT_ALW``) to your own salary structures
  that pay shift allowances.

Dependencies
============

* Installs by itself with Shifts (``om_hr_shift``) and Odoo 20 HR Payroll
  (``om_hr_payroll``).

Support
=======

Odoo Mates, odoomates@gmail.com
