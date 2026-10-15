=================
Payroll Dashboard
=================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The Payroll dashboard for the payroll officers: what the confirmed payslips pay,
month by month and across the company, without Accounting.

Features
========

* Dashboards > Human Resources > Payroll:

  * gross and net pay, employees paid, average gross and overtime paid over the
    Period;
  * gross and net pay month by month;
  * gross pay by department and by job position, the pay by category, and the
    deductions by rule;
  * the top earners of the period;
  * Period and Department filters; the companies selected in the company
    switcher.

* It reads the Payroll Analysis of the confirmed payslips, the refunds counted
  negative, and works without Accounting.

Configuration
=============

The dashboard is for the payroll officers (Payroll: Officer access).

Usage
=====

Confirm the payslips, then open Dashboards, then Payroll in the Human Resources
section, and set the Period and Department filters.

Dependencies
============

* ``spreadsheet_dashboard`` (Dashboards) and ``om_hr_payroll`` (Payroll).
  Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
