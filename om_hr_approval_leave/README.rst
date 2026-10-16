======================
HR Approvals: Time Off
======================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

An approver on validated time off is replaced, for its dates, by their substitute, else by their manager.

Features
========

* When the time off of an employee who approves is validated, a delegation of their approvals is created for its
  dates: to the substitute set in their preferences, else to their manager.
* The substitute is asked the approvals waiting for the employee meanwhile; the employee still can decide.
* The delegation follows the time off: changed dates move it, a refused or cancelled time off removes it.

Dependencies
============

* ``om_hr_approval``, Time Off (``hr_holidays``). Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
