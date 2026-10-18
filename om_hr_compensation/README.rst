=================
HR Compensation
=================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Salary grades and bands, the compa-ratio of every wage, and merit cycles: each
department gets a budget, the managers propose the raises of their team within
it, HR approves them and they become new contract versions.

Features
========

* **Salary grades**: a band of monthly wages per grade, e.g. G5 from 5,000 to
  8,000, with its midpoint (halfway by default, or the market rate you set).
  Each job position points to its grade.
* **Compa-ratio**: the wage of the employee divided by the midpoint of the
  grade of their job position, and where the wage sits in the band (below it,
  lower, middle or upper third, above it), on the employee and in the Pay
  Positioning report of the current wages, by grade, department or position.
* **Merit cycles**:

  * An HR administrator creates a cycle with its effective date and a budget, a share of the
    wages paid today (3% by default), and generates one line per employee paid,
    for all the departments or those chosen. Each department gets its budget,
    which HR may change.
  * Open for Proposals gives each manager a to-do. In Compensation > Raises of
    My Team they propose a raise per employee, as a percentage or as the new
    wage, seeing the compa-ratio before and after; the raises of a department
    stay within its budget. A manager reads only the lines of their own team.
  * HR closes the proposals, approves or refuses each raise (HR may go beyond
    the budget), and clicks Apply: each approved raise becomes a new version of
    the contract of the employee from the effective date, with the new wage.

Configuration
=============

* Compensation is for the HR administrators (Employees: Administrator), the
  users who read the wages in Odoo. The managers proposing raises read only the
  wages of their team, on their lines of a merit cycle.

* Employees > Configuration > Salary Grades (HR managers): the grades and their
  band.
* Give each job position its grade in its form.

Usage
=====

#. Compensation > Merit Cycles: create a cycle, Generate Employees, check the
   budgets, then Open for Proposals.
#. The managers propose the raises in Compensation > Raises of My Team.
#. HR clicks Close the Proposals, approves or refuses the raises, then Apply.

Dependencies
============

* HR Base (``om_hr_base``)
* Discuss (``mail``)

Support
=======

Odoo Mates, odoomates@gmail.com
