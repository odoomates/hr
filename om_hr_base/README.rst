=======
HR Base
=======

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The shared base of the Odoo Mates HR modules: what they have in common. It is
installed by the modules that need it; it gives little on its own.

Features
========

* The My HR menu: each Odoo Mates HR module adds there what the employees do
  for themselves, such as their loans, certificates, documents, assets,
  appraisals and payslips. Every internal user sees it; the menu shows once a
  module adds an entry to it.
* The Employee Category of the contract (required, the first employee type by
  default), on the contract form next to the job.
* The Employee Types menu in Employees > Configuration, in debug mode.

Dependencies
============

* Employees (``hr``)

Upgrade notes
=============

Records that move here from another Odoo Mates HR module keep their database
id: before loading its data, the module takes over their external ids. The list
of those records is kept in ``moved.py``. Today these are the Employee Category
field and the Employee Types menu, formerly owned by Payroll
(``om_hr_payroll``). Running the take-over again changes nothing.

Support
=======

Odoo Mates, odoomates@gmail.com
