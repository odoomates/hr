===========
HR Lateness
===========

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Late arrivals and early departures, counted against the working schedule and
penalised by a lateness policy.

Features
========

* Each working day with attendances, the first check-in is compared with the
  start of the working schedule and the last check-out with its end. Time off
  and public holidays are left out, so a half day off or a holiday never counts
  as late; a night shift ends the next morning; flexible schedules are skipped.
  The schedules of the shift rosters are read the same way.
* Recorded as soon as the attendance is, and again every night for the last
  week, to follow the time off and the attendances changed since.
* **Lateness policy**: grace minutes on arrival and on departure, whether early
  departures count, a monthly cap in days of wage, and a matrix of penalties: a
  band of minutes, from an occurrence in the month on, gives a warning, a fixed
  amount, a percentage of the daily wage, or the minutes at the hourly wage
  times a factor. Late arrivals and early departures are numbered apart; the
  numbering starts again each month. A *Standard* policy is provided: beyond 10
  minutes, the time late or left early at the hourly wage.
* A warning messages the employee.
* The attendance managers excuse a lateness, with a reason: it is no longer
  counted, and the numbering of the month follows. *Count Again* undoes it.
* Attendances > Management > Lateness for the managers, with a pivot by month;
  My HR > My Lateness for the employees.

With Payroll Adjustments, *HR Lateness Payroll* takes the penalties off the
payslips.

Configuration
=============

* Attendances > Configuration > Lateness Policies: the grace minutes and the
  penalties.
* Attendances > Configuration > Settings > Lateness Policy: the policy of the
  company; the employee form sets a policy of its own. Without one, the first
  policy of the company, or shared by all companies, applies.

Usage
=====

#. Employees check in and out as usual.
#. The managers review Attendances > Management > Lateness and excuse what
   should not count.
#. The employees follow theirs in My HR > My Lateness.

Dependencies
============

* ``hr_attendance``
* ``om_hr_base`` (HR Base)

Support
=======

Odoo Mates, odoomates@gmail.com
