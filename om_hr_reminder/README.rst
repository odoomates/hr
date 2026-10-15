============
HR Reminders
============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Birthdays, work anniversaries and probation ends, reminded through the
Automation Rules of Odoo, and the celebrations of the month for everyone.

Features
========

* Each employee gets a next birthday, a next work anniversary (with the years of
  service, counted from the start of the contract) and a probation end, kept up
  to date every day by a scheduled action and whenever the dates change. The
  next work anniversary shows on the employee form for HR officers.
* Ready-made Automation Rules give a to-do: to the manager on a birthday, to the
  manager and the HR responsible on a work anniversary, and to the manager 14
  days before a probation ends (left to HR Appraisals when it is installed,
  as its probation reviews do it). Without a manager user, the HR responsible
  is reminded, else the HR managers of the company.
* A birthday is only reminded and shown for the employees who let it be shown
  (Show Birthday To Employees on the employee).
* My HR > Celebrations lists the coming birthdays and work anniversaries of the
  month, for every employee.

The expiring contracts and work permits are reminded by Odoo itself, and the
expiring documents by HR Documents.

Configuration
=============

Edit the ready-made rules, turn them off, or add your own on the same dates in
Settings > Technical > Automation > Automation Rules (debug mode):

* HR: birthday of an employee, to the manager
* HR: work anniversary of an employee, to the manager and HR
* HR: probation ending, to the manager

Dependencies
============

* HR Base (``om_hr_base``)
* Automation Rules (``base_automation``)

Support
=======

Odoo Mates, odoomates@gmail.com
