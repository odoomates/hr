===================
HR Lateness Payroll
===================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Bridge between HR Lateness and Payroll Adjustments: the lateness penalties of a
month are taken off the payslips.

Features
========

* Payroll > Adjustments > Lateness Penalties: for a month, and for some or all
  employees, the latenesses are counted again, then their penalties become one
  *Lateness* adjustment per employee (type ``ADJ_LATE``, a deduction, its own
  payslip line), taken by the payslip of the month.
* Or tick *Lateness Penalties Every Month* in the Attendances settings: it runs
  on the 1st for the month before.
* The penalties: a fixed amount, a percentage of the daily wage, or the minutes
  at the hourly wage, from the wage rates of the payroll (days per month of the
  company, hours per day of the schedule), within the monthly cap of the
  policy. Warnings cost nothing.
* A penalty of minutes is left out for a contract paid on attendances: the
  Attendance Adjustment rule takes the hours missed off already.
* Computed again, or after an excuse, the adjustment follows the latenesses;
  once a confirmed payslip took it, it no longer changes and the latenesses it
  penalised are no longer excused.
* Each lateness shows its penalty amount and its adjustment; the adjustment
  lists the latenesses it penalises.

Configuration
=============

* Attendances > Configuration > Settings > *Lateness Penalties Every Month*,
  per company.
* Payroll > Configuration > Adjustment Types > *Lateness*: a deduction with no
  approval, whatever is still due taken by the final settlement of an employee
  leaving.

Usage
=====

#. Early in the month, open Payroll > Adjustments > Lateness Penalties, choose
   the month before (the default) and click *Compute*.
#. Check the adjustments, then compute the payslips of the month.

Dependencies
============

* Installs by itself with HR Lateness (``om_hr_lateness``) and Payroll
  Adjustments (``om_hr_payroll_adjustment``).

Support
=======

Odoo Mates, odoomates@gmail.com
