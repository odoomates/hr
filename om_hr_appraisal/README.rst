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

Switched on in the settings, each on its own:

* **Goal Alignment**: goals of the company and of the departments besides the
  goals of the employees. A goal serves a goal above it, and a goal served by
  others takes the average of their progress: an employee updating their goal
  moves the goal of their department and of the company. The department
  manager sets the goals of the department; everyone reads the goals of the
  company and of the departments, shown as a tree in Goal Alignment.
* **One-on-Ones**: the regular meetings of a manager with each employee. Both
  write the shared notes; the private notes of the manager are read by the
  manager and HR only, never by the employee, through the API too. The actions
  agreed on become to-dos of the person doing them. A one-on-one repeating every
  N weeks plans the next one when it is done, and it prepares the open
  appraisal of the employee, which shows them in its One-on-Ones button.
* **9-Box and Calibration**: the manager sets the potential of the employee
  (low, medium or high) next to the rating; the employee never reads it. Each
  rating has a performance level, and the two place the employee on the 9-box
  grid, from Underperformer to Star, shown by box and as a grid of counts for a
  cycle. In a calibration session HR reviews the ratings and the potentials of a
  cycle with the managers and adjusts them: each change is logged with who made
  it, the old and new value and why.
* **360 Feedback**: installs HR Appraisals: 360 Feedback (``om_hr_appraisal_survey``).

Menus:

* My HR > My Appraisals and My HR > Goals, for every employee.
* Employees > Appraisals > My Team, for the managers.
* Employees > Appraisals > Appraisals and Cycles, for the HR officers.
* Employees > Appraisals > One-on-Ones, Goal Alignment and Talent Review (9-Box,
  Calibration), and My HR > My One-on-Ones, once switched on.

Configuration
=============

* Employees > Configuration > Settings > Appraisals, per company: Probation
  Reviews (how many days before the trial period ends, 14 by default) and Plan
  the Appraisals (first after 6 months, then every 12 months, created 30 days
  ahead by default).
* The same settings switch on Goal Alignment, One-on-Ones, 9-Box and
  Calibration, and 360 Feedback, for all the companies.
* Employees > Configuration > Appraisals (HR managers): Feedback Templates,
  for the departments chosen or for everyone else, and Ratings with their
  performance level on the 9-box grid.

Usage
=====

#. Create an appraisal from Employees > Appraisals > Appraisals, or let the
   settings or a cycle create it, and click Start.
#. The employee fills in their self assessment from My HR > My Appraisals and
   clicks Submit My Assessment.
#. The manager writes the review, sets the rating and the goals, and clicks
   Mark as Done. The employee then reads the review.
#. If a raise or a promotion is decided, HR clicks New Contract Version.

Upgrade
=======

The upgrade to 20.0.1.1.0 places the ratings installed with the module on the
9-box grid: Needs Improvement low, Meets Expectations medium, Exceeds
Expectations and Outstanding high. Set the level of your own ratings in
Employees > Configuration > Appraisals > Ratings. The goals keep their employee
and company; the new features stay off until switched on in the settings.

Editions
========

Works with Odoo 20 Community and Odoo 20 Enterprise. On Enterprise, it cannot
be installed together with the Enterprise Appraisals app (``hr_appraisal``): both define
the same records. Use one or the other.

Dependencies
============

* HR Base (``om_hr_base``)
* Discuss (``mail``)

Support
=======

Odoo Mates, odoomates@gmail.com
