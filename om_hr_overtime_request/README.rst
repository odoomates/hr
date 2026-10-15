=====================
Overtime Pre-Approval
=====================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Overtime authorised in advance: the overtime the Attendances app finds is
accepted up to the hours approved for the day, and what goes beyond waits for
the manager.

Features
========

* **Overtime requests**: an employee, their manager or an attendance officer
  asks for overtime hours on a day, with a reason. The request goes along the
  approval flow *Overtime Requests* (the manager by default). Employees follow
  theirs in My HR > My Overtime Requests; the attendance officers in
  Attendances > Management > Overtime Requests.
* **Pre-approval**: with the setting on, the overtime the time rules of the
  Attendances app create is checked day by day. Up to the approved hours of the
  day it is *Authorised* and validated; an overtime crossing the limit is split
  at it; the rest is *Not Authorised* and waits.
* **Review** (Attendances > Management > Overtime to Review): the attendance
  officers managing all attendances, or an attendance officer who is the
  attendance manager or the manager of the employee, accept the overtime not
  authorised, which validates it, or reject it, which refuses it. The decision
  is kept when the overtime of the day is checked again.
* Approved later, or withdrawn by an attendance officer, a request checks the
  overtime of its day again.
* Only validated overtime is paid with *Overtime in Payroll*.

Configuration
=============

* Attendances > Configuration > Settings > *Overtime Needs Pre-Approval*, per
  company.
* Employees > Configuration > Requests > Approval Flows > *Overtime Requests*:
  the steps approving the requests, one Manager step by default.
* The time rules of the Attendances app that find the overtime.

Usage
=====

#. Before working extra hours, the employee or the manager creates an overtime
   request and sends it.
#. Once approved, the overtime of that day is authorised up to the hours asked.
#. The managers review the rest in Attendances > Management > Overtime to
   Review.

Dependencies
============

* ``hr_attendance``
* ``om_hr_approval`` (HR Approvals)

Support
=======

Odoo Mates, odoomates@gmail.com
