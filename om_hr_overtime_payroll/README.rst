===================
Overtime in Payroll
===================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Pays on the payslips the overtime of the Attendances app.

In Odoo 20 the time rules of Attendances find the overtime, e.g. beyond the
working schedule, on weekends or on public holidays, each with its salary
rate, e.g. 150% or 200%. The manager validates it, or it is validated on its
own when the company does not ask for a validation. This module pays it.

Features
========

* The validated overtime of the employee up to the end of the period, not paid
  yet, is paid by the *Overtime* rule (``OVERTIME``, category Allowance): hours
  x hourly wage x the salary rate of the time rule, or of the type of an
  attendance entered by hand. An overtime whose attendance changed since waits
  for the time rules to compute it again.
* The hourly wage is the one of an hourly contract, else the monthly wage / the
  days per month of the payroll settings (30 by default, or e.g. 21.67) / the
  hours per day of the working schedule.
* Each hour is paid once: it is linked to the payslip paying it, and becomes
  payable again if that payslip is cancelled or refunded. Overtime validated
  after its month is paid on the next payslip.
* The Overtime tab of the payslip lists what it pays; the attendances list has
  an optional *Paid On* column for the payroll officers.
* New salary structures pay the overtime: the base structure gets the rule. Add
  the Overtime rule to your own structures.

Configuration
=============

* Attendances > Configuration: the time rules and their salary rate.
* Payroll > Configuration > Settings > Worked Days: the days per month of the
  daily wage.
* With *Overtime Pre-Approval*, only the overtime authorised or accepted by the
  manager is validated, so only that is paid.

Dependencies
============

* Installs by itself with Odoo 20 HR Payroll (``om_hr_payroll``) and
  Attendances (``hr_attendance``).

Support
=======

Odoo Mates, odoomates@gmail.com
