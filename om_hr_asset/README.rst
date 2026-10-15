=========
HR Assets
=========

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The assets the company hands over to its employees, such as laptops, phones and
tools, with the history of who held each one. The assets are the equipment of
the Maintenance app, so categories, serial numbers, warranty and repairs come
from it.

Features
========

* Assign an asset to an employee, with its condition and a handover form
  printed for the employee to sign (Asset Handover Form, numbered
  ``ASSET/<year>/``). Reassign hands it over to another employee in one step.
* Return it with the condition it comes back in; a damaged asset can get a
  repair request and a charge to the employee.
* Report an asset lost, with an optional charge to the employee; mark it found
  if it turns up.
* An Asset Status on every equipment (Available, Assigned, Lost), with
  filters to find them.
* The history of every asset and of every employee: who held what, when, and
  in which condition. Changing the employee on the equipment directly, or the
  departure of an employee, is kept in the history too. The employee form has
  an Assets tab for HR officers.
* Employees see the assets in their hands in My HR > My Assets.
* With HR Exit, an exit is cleared only once the assets of the employee are
  back (HR Assets in Exits). With Payroll, the charges are deducted from the
  payslips (HR Assets in Payroll).

Menus, for the equipment managers:

* Employees > Assets > Assets, Available and Assignments.
* Employees > Configuration > Employee > Asset Categories.

Configuration
=============

* Give the people who hand over the assets the Equipment Manager rights of
  Maintenance.
* Edit the text of the handover form in the print template Asset Handover
  Form.

Usage
=====

#. Create the asset in Employees > Assets > Assets.
#. Click Assign, choose the employee, the date and the condition; the handover
   form opens to print.
#. When the asset comes back, click Return and give its condition; or click
   Report Lost.

Dependencies
============

* Maintenance - HR (``hr_maintenance``)
* HR Base (``om_hr_base``)
* Print Templates (``om_print_template``)

Support
=======

Odoo Mates, odoomates@gmail.com
