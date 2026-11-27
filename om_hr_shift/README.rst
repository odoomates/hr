======
Shifts
======

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Shift planning for teams that do not work the same hours every week: plan the
shifts on the planning Gantt chart, publish them, and the published shifts
become the working schedule of each employee, which time off, attendances,
overtime, lateness and payroll then follow. The shifts are slots of the
*Planning* app of Odoo Mates on the resource of each employee, so the same
people, conflicts and rules serve the shifts and the rest of the planning.

Features
========

* **Shift templates** (Shifts > Configuration > Shift Templates): the hours of a
  kind of shift, an unpaid break and when it starts, a short name (e.g. ``M``
  for Morning) and a color. A shift ending at or before its start ends the next
  day, e.g. a night shift 22:00-06:00. Optional: the departments and job
  positions working it, the time type of its work entries (e.g. night work paid
  at its own rate) and an allowance per shift, paid with *Shift Allowances in
  Payroll*. Morning, Evening and Night templates are provided.
* **Rotations** (Shifts > Configuration > Shift Rotations): a cycle of shifts
  and days off, e.g. *2 Mornings, 2 Nights, 2 Off* (provided). Shifts > Apply a
  Rotation lays it over a period for some employees, each one day further in
  the cycle when staggered.
* **Roster** (Shifts > Roster): the planning Gantt chart by employee, by day,
  week or month, with the open shifts on top. Drag to plan and move shifts,
  copy the period before, publish and send the schedule. Drafts are hatched,
  conflicts in red, and the time off and unavailability of the employees
  greyed.
* **Conflicts**: time off or a public holiday, unavailability, overlapping
  shifts, less rest between the shifts of two days than the minimum, more hours
  in a day or a week than the maximum. The planner sees them on the shift and
  on the Gantt chart before publishing.
* **Published shifts are the working schedule**: on its first published shift,
  an employee is rostered: a new version of the contract from that day, on a
  working schedule of their own, the days before keeping their schedule. Each
  published shift is written on it as dated lines; changed or sent back to
  draft, the schedule follows. Slots planned for a document (an order, a
  task...) are work within the schedule, not shifts.
* **Rostering** (button on the employee form): start rostering an employee from
  a date, or stop it and go back to a fixed working schedule; the shifts from
  that date on are then removed.
* **Open shifts**: a shift with no employee, optionally for a department.
  Employees see the upcoming ones in My HR > Open Shifts and claim one, if the
  department and the job positions of the shift fit.
* **Shift swaps**: an employee offers a shift of theirs for a published shift of
  a colleague; the colleague accepts or declines. Claims and accepted swaps go
  along the approval flow (the manager by default); approved, the shifts change
  hands. Planners follow all requests in Shifts > Shift Requests.
* **Unavailability**: the employees tell the days they cannot work (My HR > My
  Unavailability); they are time off of their resource, shown on the roster and
  as conflicts. The planners see them all in Shifts > Unavailability.
* Employees see their published shifts in My HR > My Shifts.
* Shifts list, calendar and pivot views.

Upgrading from the former Shifts
================================

The shifts, templates, rotations, shift requests (with their approvals) and
unavailability of the former versions are moved to the planning when the module
is updated, with the same moments, states and links: published shifts keep
their lines of the working schedule and their payslip, requests waiting for an
approval keep waiting for it. The minimum rest and the maximum hours per week of
the companies become their planning rules.

Configuration
=============

* Access rights, application *Shifts*: **Planner** plans and publishes the
  shifts and plans with the *Planning* app (the HR officers are planners too);
  **Administrator** also sets the shift templates and the rotations.
* Shifts > Configuration > Settings: the planning rules per company: minimum
  rest between the shifts of two days, maximum hours per day and per week; 0
  turns a check off.
* Employees > Configuration > Requests > Approval Flows > *Shift Requests*: the
  steps approving the claims and the swaps, one Manager step by default.

Usage
=====

#. Set the shift templates and, if you work in cycles, the rotations.
#. Open Shifts > Roster and plan the shifts of the employees, or apply a
   rotation.
#. Check the conflicts, then publish: the working schedule of the employees
   follows the shifts.
#. Leave a shift without an employee to offer it as an open shift.

Dependencies
============

* ``om_planning`` (Planning)
* ``om_planning_hr`` (Planning - Employees)
* ``hr_work_entry``
* ``om_hr_base`` (HR Base)
* ``om_hr_approval`` (HR Approvals)

Support
=======

Odoo Mates, odoomates@gmail.com
