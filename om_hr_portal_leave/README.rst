=====================
 HR Portal: Time Off
=====================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees see what time off they have left and ask for time off on the website portal.

Features
========

* A **Time Off** card on My HR opens ``/my/hr/time-off``.
* The balances: for each type of time off given by allocation, what is left of what was given, in days
  or hours, as in the backend.
* **Ask for Time Off**: the type, the first and the last day, and a description. The request then
  follows the usual Time Off approval.
* The last 50 requests of the employee, with the dates, the duration and the status. A request not
  approved yet can be withdrawn; an approved one is cancelled by HR.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Configuration
=============

The types offered are those that can be selected for time off, of no country or of the country
of the company of the employee.

Usage
=====

#. The employee opens **My HR > Time Off**, checks the balance and sends a request.
#. To take back a request not approved yet, they click **Withdraw**.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``hr_holidays`` (Time Off)

Installs by itself with HR Portal and Time Off.

Support
=======

Odoo Mates, odoomates@gmail.com
