===================
 HR Portal: Shifts
===================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees follow their shifts and ask for changes on the website portal.

Features
========

* A **Shifts** card on My HR opens ``/my/hr/shifts``.
* **My Upcoming Shifts**: the published shifts of the employee from today on.
* **Open Shifts**: the published open shifts of their company the employee may claim; **Claim** sends
  the claim for approval.
* **Swap a Shift**: one of their shifts against a published shift of a colleague of the same
  department, with a word for the colleague; the request goes to the colleague.
* **Swaps Asked of You**: the colleague asked accepts or declines the swap.
* **Days I Cannot Work**: add or remove the days the employee is not available.
* The last 20 requests made by or asked of the employee, with whom they wait for and their status.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

#. The employee opens **My HR > Shifts**.
#. They claim an open shift, ask a colleague for a swap, answer the swaps asked of them, or add the
   days they cannot work.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_shift`` (Shifts)

Installs by itself with HR Portal and Shifts.

Support
=======

Odoo Mates, odoomates@gmail.com
