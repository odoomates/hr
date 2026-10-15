==================
HR Exit in Payroll
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The bridge between HR Exit and Payroll: the final settlement payslip of an
exit, with the last salary, the unused time off paid out, the end of service
gratuity and the loans still due.

Features
========

* Final Settlement (payroll officers), on an approved or closed exit: creates
  the payslip "Final Settlement of" the employee, from the first day of the
  month of the last working day to the last working day, with the contract,
  the structure, the worked days and the inputs of that period, and computes
  it. The Final Settlement button at the top of the exit opens it.
* The final settlement pays up to the last working day, even before the
  departure ends the contract.
* Unused time off: the days left on the allocations of the time types paid
  out at the exit, on the last working day, are paid at the daily wage, the
  monthly wage over the days per month of the payroll settings. The exit
  shows the days and the amount (HR officers). Salary rule Unused Time Off (code
  ``LEAVE_ENCASH``, category Allowance).
* End of service gratuity: with HR Gratuity, the gratuity of the exit is paid
  by the salary rule End of Service Gratuity (code ``GRATUITY``, category
  Allowance).
* Loans: with HR Loans in Payroll, the final settlement deducts every loan
  installment still due, whatever its month.
* The amounts are read again from the exit each time the payslip is
  computed.

Configuration
=============

* Employees > Configuration > Time Management > Time Types, Payroll tab: tick
  Paid Out at the Exit on the time off to pay out.
* Payroll > Configuration > Settings, Daily Wage: the days per month the
  monthly wage is divided by, for the unused time off.
* The rules Unused Time Off and End of Service Gratuity are added to the
  structure "Base for new structures". The structures that already exist are
  left as they are: add both rules to them in Payroll > Configuration >
  Salary Structures, with the Partial Period rule of the payroll to prorate
  the last salary; without it the whole wage of the last month is paid.

Usage
=====

#. Approve the exit (HR Exit), and compute its gratuity with HR Gratuity.
#. Click Final Settlement: the payslip is created and computed.
#. Check it, and confirm it as any payslip.

Dependencies
============

* HR Exit (``om_hr_exit``)
* Payroll (``om_hr_payroll``)

Installs by itself with HR Exit and Payroll.

Support
=======

Odoo Mates, odoomates@gmail.com
