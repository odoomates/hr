============================
 HR Portal: Pay Adjustments
============================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Shows the employees the bonuses, commissions and deductions of their pay on the website portal.

Features
========

* A **Pay Adjustments** card on My HR opens ``/my/hr/adjustments``: the running and done adjustments of
  the employee, with the type, addition or deduction, the start month, the amount each month (fixed,
  or a percentage of its base) and what is already done.
* ``/my/hr/adjustments/<id>``: the detail of one adjustment, its recurrence, the total when it has one,
  and each monthly line with its amount and status.
* The drafts and the adjustments waiting for approval stay with the payroll and are not shown.
* Read only: the adjustments are made by the payroll in the backend.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

The employee opens **My HR > Pay Adjustments** on the portal and clicks an adjustment to see its months.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_payroll_adjustment`` (Payroll Adjustments)

Installs by itself with HR Portal and Payroll Adjustments.

Support
=======

Odoo Mates, odoomates@gmail.com
