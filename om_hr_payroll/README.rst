==================
Odoo 18 HR Payroll
==================

Payroll for Odoo 18 Community Edition: salary structures and rules, employee
payslips, payslip batches and the payslip reports.

Features
========

* Compute a payslip for an employee over a period, with its worked days, its
  other inputs and one line per salary rule that applies.
* Move a payslip through Draft, Waiting, Done and Rejected, and refund a
  confirmed payslip.
* Build salary structures out of salary rules, and give a structure a parent so
  that it also applies the rules of the structure above it.
* Write a salary rule as a fixed amount, as a percentage of another figure or
  as Python code, and apply it always, only inside an amount range, or on a
  Python condition.
* Group rules in categories such as Basic, Allowance, Gross, Deduction and Net,
  and use a category total inside another rule.
* Take the worked days from the working schedule of the employee, with a line
  per type of time off of the period.
* Give a time off type a code, read by the salary rules as
  ``worked_days.CODE``.
* Fill the House Rent, Dearness, Travel, Meal, Medical and Other allowances on
  the contract; the base structure installs a rule for each of them.
* Generate the payslips of a batch for the employees you select, then confirm
  the whole batch.
* Print the PaySlip and the PaySlip Details PDF reports from a payslip, and the
  PaySlip Lines By Contribution Register report for a register over a period.
* Send a payslip to the employee by email, with the payslip attached.
* Record the third parties who collect or inject money on payslips as
  contribution registers.
* Number confirmed payslips from the Salary Slip sequence.
* Payroll officers work on the payslips, the salary structures and the salary
  rules; payslip batches are for payroll managers.

Installation
============

To install this module, you need to:

Download the module and add it to your Odoo addons folder. Afterward, log on to
your Odoo server and go to the Apps menu. Trigger the debug mode and update the
list by clicking on the "Update Apps List" link. Now install the module by
clicking on the install button.

Configuration
=============

* Give your users their Payroll access in Settings > Users & Companies > Users:
  Officer for the people who prepare payslips, Manager for the people who also
  run the payslip batches.
* Review the salary rules and the salary structures in Payroll > Configuration.
* Add the third parties you pay through payslips as Contribution Registers, and
  point the relevant salary rules at them.
* Fill the wage of each employee and pick the salary structure on the contract.
* To also post the payslips in accounting, tick Payroll Entries in Payroll >
  Configuration > Settings, which installs the payroll accounting module.

Usage
=====

* For one employee, go to Payroll > Employee Payslips, create a payslip, choose
  the employee and the period, click Compute Sheet, then confirm it.
* For a group of employees, go to Payroll > Payslips Batches, create a batch
  for the period, use Generate Payslips to pick the employees, then close the
  batch once the payslips are right.
* Print the payslip from the Print menu of the payslip, or send it with Send by
  Email.

Editions
========

Works with Odoo 18 Community and Odoo 18 Enterprise. On Enterprise, it cannot
be installed together with the Enterprise Payroll app (``hr_payroll``): both
define the same records. Use one or the other.

Dependencies
============

* Discuss (``mail``)
* Employee Contracts (``hr_contract``)
* Time Off (``hr_holidays``)

Support
=======

Odoo Mates, odoomates@gmail.com

Contributors: Odoo Mates <odoomates@gmail.com>, Odoo SA.
