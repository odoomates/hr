=================================
Time Off and Attendance Dashboard
=================================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The Time Off and Attendance dashboard for the HR officers: the time off taken
and waiting for approval, the hours worked and the overtime.

Features
========

* Dashboards > Human Resources > Time Off and Attendance:

  * time off taken (days), requests to approve, hours worked and overtime hours
    over the Period, and month by month;
  * the time off by type and by department, the hours worked and the overtime by
    department;
  * the list of the time off requests to approve;
  * Period and Department filters; the companies selected in the company
    switcher.

* The time off counts the approved requests; the hours count the validated
  attendances. The overtime is the attendances the time rules of the
  Attendances app create.
* A stored Department (Dashboard) field on the attendances, the department of
  the employee, to group and filter them by department.

Configuration
=============

The dashboard is for the HR officers (Employees: Officer access).

Usage
=====

Open Dashboards, then Time Off and Attendance in the Human Resources section,
and set the Period and Department filters.

Dependencies
============

* ``spreadsheet_dashboard`` (Dashboards), ``hr_holidays`` (Time Off) and
  ``hr_attendance`` (Attendances). Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
