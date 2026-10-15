=============
HR Appraisals
=============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Appraise the employees: they assess themselves, their manager reviews and
rates them, and they set goals for the next period.

Features
========

* An appraisal goes To Start, Self Assessment, Manager Review, Done. Each step
  gives a to-do to the person whose turn it is: the employee, then the manager
  (or the HR responsible of the employee when there is no manager user). The
  manager can send the self assessment back to the employee to complete it.
* The employee and the manager each write a feedback started from a template,
  per department if you like. The manager reads the self assessment once it is
  submitted; the employee reads the review of the manager once the appraisal
  is done. This holds through the API too, not only on screen.
* An overall rating on a scale you set, e.g. Needs Improvement to Outstanding,
  required to close the appraisal, and a meeting date.
* Goals with a target, a due date and a progress: the manager sets them, the
  employee updates the progress of their own goals. A goal at 100% is reached.
* Probation reviews: a review for the manager is created before the End of
  Trial Period of the contract; it skips the self assessment.
* Planned appraisals: the first one some months after an employee joins, then
  every N months, created ahead of time by a daily job, one open appraisal at a
  time per employee.
* Review cycles: the annual review of departments or of chosen employees, one
  appraisal each, started at once, with the progress of the cycle. Employees
  added later get theirs with Add New Employees.
* A raise or a promotion decided in an appraisal is recorded with New Contract
  Version: the employee opens on a new version of their contract from a date,
  where HR changes the wage, the job or the department. A version dated in the
  past is paid by the Retro Pay of the payroll.
* The employee form shows the number of appraisals and the date of the next
  one (Appraisals smart button, for HR officers).

Menus:

* My HR > My Appraisals and My HR > Goals, for every employee.
* Employees > Appraisals > My Team, for the managers.
* Employees > Appraisals > Appraisals and Cycles, for the HR officers.

Configuration
=============

* Employees > Configuration > Settings > Appraisals, per company: Probation
  Reviews (how many days before the trial period ends, 14 by default) and Plan
  the Appraisals (first after 6 months, then every 12 months, created 30 days
  ahead by default).
* Employees > Configuration > Appraisals (HR managers): Feedback Templates,
  for the departments chosen or for everyone else, and Ratings.

Usage
=====

#. Create an appraisal from Employees > Appraisals > Appraisals, or let the
   settings or a cycle create it, and click Start.
#. The employee fills in their self assessment from My HR > My Appraisals and
   clicks Submit My Assessment.
#. The manager writes the review, sets the rating and the goals, and clicks
   Mark as Done. The employee then reads the review.
#. If a raise or a promotion is decided, HR clicks New Contract Version.

Dependencies
============

* HR Base (``om_hr_base``)
* Discuss (``mail``)

Support
=======

Odoo Mates, odoomates@gmail.com
