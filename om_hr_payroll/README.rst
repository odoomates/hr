==================
Odoo 20 HR Payroll
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Payroll for Odoo 20 Community Edition: salary structures and rules, employee
payslips, payslip batches and the payslip reports.

Features
========

* Compute a payslip for an employee over a period, with its worked days, its
  other inputs and one line per salary rule that applies.
* Move a payslip through Draft, Waiting, Done and Rejected, with the whole
  history and the messages kept on the payslip itself.
* Build salary structures out of salary rules, and give a structure a parent so
  that it also applies the rules of the structure above it.
* Write a salary rule as a fixed amount, as a percentage of another figure or
  as Python code, and apply it always, only inside an amount range, or on a
  Python condition.
* Group rules in categories such as Basic, Allowance, Gross, Deduction and Net,
  and use a category total inside another rule.
* Describe what your company pays besides the wage as salary components, e.g.
  Housing or Transport, and set their amount on the employment version of each
  employee. A salary rule reads a component with ``components.HOUSING``, so the
  same module serves any country without a field per allowance.
* Start from the rules the module installs in its base structure: Basic
  Salary, Hourly Pay, Unpaid Time Off, Attendance Adjustment, Partial Period,
  Allowances, Retro Pay, Deductions, Gross and Net. Allowances pays every
  component of the Allowance category and Deductions subtracts every component
  of the Deduction category, so a new component is paid without writing a rule; give a component
  its own rule when it has to appear on its own line of the payslip.
* Take the time off that is not paid off the payslip automatically. How much of
  a time off is paid comes from its Time Type: nothing is taken off a time off
  paid in full, the whole of an unpaid one, and half of a time off whose rate is
  50%. A closing day of the company carries no time type and is paid. The rule
  belongs to the Basic category, so the gross of the payslip is what was really
  earned in the period, and the taxes computed on it are right.
* Pay from the work entries of Odoo: the working schedule less the time off, or
  the validated attendances and the time off for the contracts marked Attendance
  Based. A contract based on attendances on a fixed wage loses the hours it was
  due to work but neither worked nor took as time off (Attendance Adjustment).
* Pay by the hour: a contract with an Hourly Wage is paid its hours worked, and
  its time off at the paid rate of its time type, by the Hourly Pay rule. The
  overtime stays paid by the overtime rule only.
* One daily wage for the payroll: the monthly wage over the days per month you
  set (30 by default, or e.g. 21.67), used by the unused time off, the overtime,
  and the rules through ``daily_wage`` and ``hourly_wage``.
* Pay the part of the period an employee joining or leaving was under contract.
  The Partial Period rule takes off the wage of the working days outside the
  contract; a monthly wage is measured against the calendar month, so a payslip
  up to the last working day pays the days worked out of the whole month.
* Write your own rules against the worked days with
  ``worked_days.unpaid_ratio()``, the part of the period that is not paid,
  ``worked_days.scheduled_days()``, the days the employee was due to work,
  ``worked_days.scheduled_hours()``, ``worked_days.paid_hours()``,
  ``worked_days.missing_hours()``, and
  ``worked_days.prorata()``, the share of the period the contract covers.
* Round the amount of a salary rule to the nearest, up or down, to a multiple
  you choose, e.g. 1.0 for whole amounts or 5.0.
* Pay a raise dated back to a past month with Retro Pay on a draft payslip: the
  payslips confirmed since the date you give are computed again with the
  contracts as they stand now, and what they would have paid more in the Basic
  and Allowance categories is added to the payslip as the Retro Pay input.
* Keep the rates, the thresholds and the ceilings out of the salary rules as
  rule parameters, each with its values by date. A rule reads one with
  ``parameters.SS_RATE``, and the value taken is the one of the period being
  paid, so a payslip computed again for an old period stays right. Changing a
  rate next year is entering a value in Payroll > Configuration > Rule
  Parameters, not editing the code of a rule.
* Enter the bands of a tax or of a contribution as a salary bracket instead of
  writing them in code, and compute an amount from them in one line:
  ``result = -brackets.INCOME_TAX.compute(categories.GROSS)``. A bracket holds a
  table per date, and a table per key when the same scale has one per filing
  status, per state or per pay frequency:
  ``brackets.FED_TAX.compute(base, key=employee.filing_status)``. The bands are
  applied in the way the country asks for: marginal, each band on its own slice;
  excess, the fixed amount of the band plus its rate on what exceeds its floor;
  or flat, on the whole amount.
* A rule reading a parameter or a bracket that is not configured, or that has no
  value on the date of the payslip, stops the payslip and names what is missing:
  a rate quietly worth zero would be a payslip that is wrong without saying so.
* Payroll managers own the parameters and the brackets, payroll officers read
  them: a rate is changed without giving anyone the right to write Python.
* Compute on what the employee has already been paid this year with
  ``ytd.GROSS``, the total of a salary rule over the payslips of the year
  already confirmed. Refunds are taken back, the payslips still draft do not
  count, and the year is the fiscal year of the company, so a company closing in
  March has a payroll year running April to March without anything more to set.
  The payslip being computed is not part of it: a rule needing the year
  including this period writes ``ytd.GROSS + categories.GROSS``, which says so
  and does not depend on the order the rules are computed in.
* Use it for what has to be counted over the year: a contribution stopping at a
  yearly ceiling, a tax computed on the year and spread over the periods, or a
  payslip showing its year to date.
* Stop a contribution at a yearly ceiling in one line: a rule SS_BASE computing
  ``result = ytd.capped('SS_BASE', categories.GROSS, parameters.SS_CEILING)``
  gives the part of this month's base still under the ceiling, and the
  contribution is a rate of it, ``result = -SS_BASE * parameters.SS_RATE``.
* Print the annual statement of the employees: what each one was paid over the
  payroll year, salary rule by salary rule and month by month, from the
  confirmed payslips, refunds taken back. The payroll year is the fiscal year of
  the company. Employees download their own statement of last year from My HR >
  My Payslips, and of every year from the portal with HR Portal: Payslips.
* Generate the payslips of a batch for the employees you select, then confirm
  the whole batch in one step; employees belonging to another company than the
  batch are refused.
* Check a batch before it is confirmed: Mark as Done first lists the payslips
  whose gross or net pay changes by more than 10% from the last confirmed
  payslip of the employee, with the salary rule that moved most, and the
  employees paid for the first time. Open a payslip to check it, or confirm
  anyway: the list stays in the chatter of the batch.
* Send a confirmed payslip to the employee by email, from the payslip or for a
  whole batch at once, with the payslip attached; the employees who have no
  work email are named back to you instead of being skipped silently.
* Print the PaySlip and the PaySlip Details PDF reports from a payslip, and the
  PaySlip Lines By Contribution Register report for a register over a period.
* Analyse the payslip lines in Payroll > Reporting > Payroll Analysis (pivot,
  graph and list), by employee, department, job position, salary rule category
  or month; the lines of the refunds count negative. The Salary History button
  of an employee opens the same analysis for that employee, month by month.
* Record the third parties who collect or inject money on payslips as
  contribution registers, and read back the payslip lines that belong to them.
* Refund a payslip: a credit note taking back its lines as they were paid is
  created and confirmed.
* Number confirmed payslips from the Salary Slip sequence, and take the worked
  days and the leaves from the working schedule of the employee.
* Employees see their own confirmed payslips in My HR > My Payslips and
  download them as PDF, the light users of Odoo 20 included. Nobody reaches
  another employee's payslip, nor a draft or a refund, through the screens, the
  download links or the API.
* Payroll officers work on payslips, payslip lines, inputs and worked days,
  while salary structures, salary rules, salary rule categories, rule inputs
  and contract advantage templates are read-only for them and managed by
  payroll managers. Payslip batches are for payroll managers only.
* A payroll officer cannot confirm, reject or reset their own payslip; a
  payroll manager does it for them.
* In a multi-company database, payslips, payslip lines, inputs, worked days,
  batches, structures, rules and categories are limited to the companies the
  user is allowed to work in.
* A payslip can only be deleted while it is draft or rejected, and a batch only
  while it is draft.

Installation
============

To install this module, you need to:

Download the module and add it to your Odoo addons folder. Afterward, log on to
your Odoo server and go to the Apps menu. Trigger the debug mode and update the
list by clicking on the "Update Apps List" link. Now install the module by
clicking on the install button.

Upgrade
=======

To upgrade this module, you need to:

Download the module and add it to your Odoo addons folder. Restart the server
and log on to your Odoo server. Select the Apps menu and upgrade the module by
clicking on the upgrade button.

Since 2.2.0 the module depends on HR Base (om_hr_base): add both modules to the
addons folder. Until the module is upgraded, the server skips it and the Payroll
menu is missing; the upgrade installs HR Base.

The upgrade to 2.4.0 adds the variance check of the payslip batches, at 10%
for every company: set another threshold, or 0 to turn it off, in Payroll >
Configuration > Settings. It also adds the annual statement and ``ytd.capped``.
From 2.4.0 a refund takes back the lines of the payslip it refunds as they
were paid, where it used to compute the payslip again: after a raise, a new
rate or a time off validated since, it took back what the payslip would pay
today. The refunds made before stay as they are. To pay what a payslip should
have paid, use Retro Pay.

The upgrade to 2.3.0 checks the companies of the payroll in a multi-company
database: a contract, payslip, batch, structure or rule now only links records
of its own company, or records shared by all the companies. Nothing is changed
by the upgrade: the records already linking another company are listed as
warnings in the server log, and the next change of such a record asks to fix
its link first. The bracket tables, rule parameters, rule inputs and advantage
templates now follow the company too.
The payslip lines now belong to the company of their payslip: the upgrade
corrects the lines computed from another company, which only happened in a
multi-company database.

The upgrade to 2.2.0 fixes the total of a salary rule category reaching exactly 0
on a payslip: it was replaced by the last amount added, e.g. a whole month of
unpaid time off paid minus the wage instead of nothing.

The upgrade to 2.2.0 fixes the rules of a structure and of its parents: a rule
of a child structure now always overrides the rule of the same code of its
parent, where the database ids used to decide, and a payslip without a structure
of its own, or computed over several contract versions, no longer leaves out the
rules of the parent structures.

The upgrade to 2.2.0 keeps the worked days of your companies computed from the
working schedule, as before. To pay from the work entries, e.g. the contracts
based on attendances, choose Work Entries in Payroll > Configuration > Settings
> Worked Days, and add the Hourly Pay and Attendance Adjustment rules to your
structures.

The upgrade to 2.2.0 lets the employees read their own confirmed payslips in
My HR > My Payslips: their other payslips, the drafts and the refunds stay
hidden.

The upgrade to 2.2.0 adds the Partial Period and Retro Pay rules without adding
them to your salary structures, so the payslips stay as they were. Add them to
the structures that should use them: without Partial Period, a payslip of an
employee joining or leaving during the period pays the whole wage.

Configuration
=============

* Give your users their Payroll access in Settings > Users & Companies >
  Users: Officer for the people who prepare payslips, Manager for the people
  who own the salary structures and the batches.
* Review the salary rules and the salary structures in Payroll > Configuration
  > Salary Rules and Payroll > Configuration > Salary Structures. The module
  installs a set of rules you can use as they are or adapt.
* Add the third parties you pay through payslips in Payroll > Configuration >
  Contribution Registers, and point the relevant salary rules at them.
* Describe what you pay besides the wage in Payroll > Configuration > Salary
  Components, e.g. a Housing component with the code ``HOUSING``. Put it in the
  Allowance category to have it paid, or in the Deduction category to have it
  subtracted.
* Fill the wage and the salary components of each employee, and pick the salary
  structure, in Payroll > Employees > Contracts.
* Set the variance threshold of the payslip batches in Payroll > Configuration
  > Settings, 10% by default, or 0 to confirm the batches without the check.
* To also post the payslips in accounting, tick Payroll Entries in Payroll >
  Configuration > Settings, which installs the payroll accounting module.

Usage
=====

* For one employee, go to Payroll > Employee Payslips, create a payslip, choose
  the employee and the period, click Compute Sheet, then confirm it.
* For a group of employees, go to Payroll > Payslips Batches, create a batch
  for the period, use Generate Payslips to pick the employees, then Mark as
  Done once the payslips are right.
* Print the payslip from the Print menu of the payslip, or send it to the
  employee with Send by Email on a payslip, or Send Payslips by Email on a batch.
* For the annual statements, go to Payroll > Reporting > Annual Statements, or
  select employees and use Annual Statement in their Action menu, choose the
  year and print.
* To pay a raise dated back to a past month, open a draft payslip, click Retro
  Pay and give the date from which the confirmed payslips are computed again.

Dependencies
============

* Discuss (``mail``)
* Time Off (``hr_holidays``)
* HR Base (``om_hr_base``)

Support
=======

Odoo Mates, odoomates@gmail.com

Contributors: Odoo Mates <odoomates@gmail.com>, Odoo SA.
