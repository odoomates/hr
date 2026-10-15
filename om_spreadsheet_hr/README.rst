=============
HR Dashboards
=============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The Workforce dashboard for the HR officers, and spreadsheet formulas that count
the employees under contract, the joiners and the leavers on any date.

Features
========

* Dashboards > Human Resources > Workforce:

  * headcount, joiners, leavers, turnover and average service (years) over the
    Period, and the headcount, joiners and leavers month by month;
  * the employees by department, job position, nationality and type;
  * the contracts ending in the period, archived employees included;
  * Period and Department filters; the figures cover the companies selected in
    the company switcher.

* The OM.HR formulas, usable in any spreadsheet:

  * ``OM.HR.HEADCOUNT(date, departments)``: the employees under contract on a
    date, the archived ones included for the past;
  * ``OM.HR.JOINERS(date_from, date_to, departments)`` and
    ``OM.HR.LEAVERS(date_from, date_to, departments)``: the employees whose
    contract started or ended between the two dates;
  * ``OM.HR.TENURE(date, departments)``: the average service in years, counted
    from the first contract of each employee.

  Departments are names separated by commas, e.g.
  ``ODOO.FILTER.VALUE("Department")``; empty for all. An empty date means today.

Configuration
=============

The dashboard and the formulas are for the HR officers (Employees: Officer
access); other users get an access error from the formulas.

Usage
=====

Open Dashboards, then Workforce in the Human Resources section, and set the
Period and Department filters. The figures read the contract dates of the
employees: fill in the contract start and end dates on the employees.

Dependencies
============

* ``spreadsheet_dashboard`` (Dashboards) and ``hr`` (Employees). Installs by
  itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
