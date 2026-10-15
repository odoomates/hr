=======
HR Exit
=======

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Employee exits, from the notice to the departure: a resignation, or a
contract HR ends, approved along an approval flow, cleared with a checklist
during the notice period, then registered as the departure of the employee.

Features
========

* My HR > My Resignation: an employee gives notice, with the reason and the
  details, and submits it. HR records an exit for any employee the same way,
  e.g. a termination, from Employees > Exits > All Exits.
* The last working day is the notice date plus the notice period of the
  company, and can be changed until the exit is approved. An employee has one
  exit in progress at a time.
* The exit is approved along the Exits approval flow: the manager of the
  employee, then the HR administrators. Approvers find it under Employees >
  Exits > To Approve, or My HR > To Approve. A draft or an exit to approve can
  be withdrawn.
* Once approved, the exit is in its notice period: it gets a clearance line
  per item of the exit checklist that applies to its reason, each with the
  users who clear it and a to-do for them due on the last working day.
* Employees > Exits > To Clear: the lines a user has to clear. Each is marked
  Cleared or Not Needed by its users or by HR, which closes the to-do; HR can
  reopen a line. The exit shows how much is cleared.
* Register Departure (HR officers), once every line is closed: the departure
  is created in core HR with the reason, the details, the notice date and the
  last working day; the contract ends on the last working day, and the
  employee is archived the day after.
* Cancel Exit (HR officers): the employee stays after all. The exit is
  cancelled, its pending lines are marked Not Needed, and the departure is
  cancelled when not applied yet.
* The Exit Interview tab (HR officers): the date, whether the employee would
  come back, and the notes of the interview.
* Five checklist items come with the module: Work Handed Over and Company
  Property Returned (the manager), Accesses Removed (the system
  administrators), Dues Settled (the HR administrators) and Exit Interview
  (the HR officers, for a resignation or a retirement only).

Configuration
=============

* Employees > Configuration > Settings, Exits: the Notice Period in days
  (30 by default), per company.
* Employees > Configuration > Requests > Exit Checklist (HR administrators):
  the items, who clears each (the manager of the employee, the manager of the
  department, the HR responsible of the contract, the users of a group, or
  given users), the departure reasons it applies to (empty: all), the company
  and a description. When nobody is found, the HR administrators clear the
  item; the leaving employee never clears his own.
* Employees > Configuration > Requests > Approval Flows: the Exits flow, its
  steps and their approvers (HR Approvals).

Usage
=====

#. The employee submits his resignation in My HR > My Resignation, or HR
   creates the exit.
#. The manager, then HR, approve it.
#. During the notice period, the people of the checklist clear their lines.
#. HR clicks Register Departure.

Related modules, installed on their own when their dependencies are:

* HR Exit in Payroll: the final settlement payslip of the exit.
* HR Assets in Exits: the exit is cleared once the employee's assets are back.
* HR Portal: Resignation: employees resign and follow their exit on the
  website portal.

HR Gratuity, installed by hand, adds the end of service gratuity to the exit.

Dependencies
============

* HR Approvals (``om_hr_approval``)

Support
=======

Odoo Mates, odoomates@gmail.com
