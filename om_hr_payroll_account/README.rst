=============================
Odoo 18 HR Payroll Accounting
=============================

This module connects the Odoo 18 Community payroll to the accounting: each
confirmed payslip posts a journal entry built from the debit and credit accounts
of the salary rules.

Features
========

* Each salary rule gets a Debit Account, a Credit Account, an Analytic Account
  and a Tax on an Accounting tab.
* Each payslip gets a Salary Journal, an accounting date and a link to the
  journal entry it created.
* The salary journal and the analytic account can be set on the contract;
  payslip batches get their own salary journal, taken by the payslips generated
  from the batch.
* Confirming a payslip creates the journal entry and posts it: one debit and
  one credit line per salary rule, dated on the accounting date of the payslip,
  or the end of its period.
* The partner of a journal item is taken from the contribution register of the
  salary rule.
* When the debits and the credits do not match, an adjustment line is added on
  the default account of the salary journal.
* Confirming a payslip whose salary rules have no debit and credit account is
  refused with a message.
* A refund payslip posts the opposite entry, and cancelling a payslip deletes
  its journal entry.

Installation
============

To install this module, you need to:

Download the module and add it to your Odoo addons folder. Afterward, log on to
your Odoo server and go to the Apps menu. Trigger the debug mode and update the
list by clicking on the "Update Apps List" link. Now install the module by
clicking on the install button.

The module can also be installed from Payroll > Configuration > Settings,
Payroll Entries.

Configuration
=============

Set the debit and credit accounts of the salary rules in Payroll > Configuration
> Salary Rules, on the Accounting tab of each rule. The analytic account and the
tax of the rule are optional.

Make sure the salary journal has a default account, so that the adjustment line
can be posted.

Usage
=====

Create a payslip in Payroll > Employee Payslips, or a batch in Payroll >
Payslips Batches. Check the salary journal and the accounting date, compute the
payslip and confirm it: the journal entry is created and posted, and is
available from the payslip.

Dependencies
============

* Odoo 18 HR Payroll (``om_hr_payroll``)
* Invoicing (``account``)

Support
=======

Odoo Mates, odoomates@gmail.com

Contributors: Odoo Mates <odoomates@gmail.com>, Odoo SA.
