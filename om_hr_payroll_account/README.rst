=============================
Odoo 20 HR Payroll Accounting
=============================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

This module connects the Odoo 20 Community payroll to the accounting: each confirmed payslip posts a
journal entry built from the debit and credit accounts of the salary rules, and the net salaries are
paid from the payslips.

Features
========

Journal entries
---------------

* Each salary rule gets a Debit Account, a Credit Account, an Analytic Account and a Tax on an
  Accounting tab. They are set per company: a salary rule shared by the companies keeps its own
  accounts in each of them, and the entry of a payslip uses the accounts of its company.
* Each payslip gets a Salary Journal, an accounting date and a link to the journal entry it created.
* The salary journal of a payslip defaults to the first miscellaneous journal of the company of the
  payslip; the journal set on the employee contract is used when there is one.
* The accounting date of the payslip can be left empty, in which case the end date of the period is
  used.
* Confirming a payslip creates the journal entry and posts it: one debit and one credit line per salary
  rule category line, with the analytic distribution and the tax of the rule.
* The partner of a journal item is taken from the contribution register of the salary rule, and is also
  set when the account of the rule is a receivable or payable account. The net salary credited is set
  on the employee, so that its payment can be matched with it.
* When the debits and the credits do not match, an adjustment line is added on the default account of
  the salary journal; the entry is refused when that journal has no default account.
* Confirming a payslip whose salary rules have no debit and credit account is refused with a message.
* A refund payslip posts the opposite entry, so the books follow the cancellation.
* Cancelling a payslip deletes its journal entry, after a confirmation on the button.
* When the journal entry cannot be deleted, for instance because it falls inside a lock date, the
  cancellation is refused with a message asking to reverse the entry in Accounting first.
* When the entry has already been reversed by a posted reversal, cancelling the payslip leaves the entry
  and its reversal in the books.
* The salary journal of a payslip must belong to the company of the payslip; the entry is created in
  that company.
* Payslip batches get their own Salary Journal, shown in the list, the form and the filters of the
  batches, and the payslips generated from a batch take the journal of the batch.
* Consolidated Entry on a payslip batch posts one entry for the whole batch when it is marked as done,
  by company and salary journal: the journal items of the same salary rule are added up, while what is
  owed to each employee stays on its own line.
* Payroll officers can confirm payslips without any accounting rights: the entry is created with the
  configuration of the salary rules, and they are given read access on the journals, accounts and taxes.
* Employee contracts get an Analytic Account and a Salary Journal, used by the payslips of the employee.

Salary payments
---------------

* Register Payment on a confirmed payslip, and Register Payments on a payslip batch, open Pay
  Salaries: a bank or cash journal, a payment method, a payment date and a memo. Each employee gets
  one payment of what is left to pay, matched with the net salary of the journal entry of the
  payslips; the amount can be changed when a single employee is paid.
* Each payslip shows its Payment Status: Not Paid, In Payment, Partially Paid, Paid, or Reversed for a
  payslip refunded before being paid, with ribbons on the form and the To Pay and Paid filters.
* The payslips and the batches show their payments.

Installation
============

To install this module, you need to:

Download the module and add it to your Odoo addons folder. Afterward, log on to
your Odoo server and go to the Apps menu. Trigger the debug mode and update the
list by clicking on the "Update Apps List" link. Now install the module by
clicking on the install button.

The module can also be installed from Payroll > Configuration > Settings, Payroll Entries.

Upgrade
=======

To upgrade this module, you need to:

Download the module and add it to your Odoo addons folder. Restart the server
and log on to your Odoo server. Select the Apps menu and upgrade the module by
clicking on the upgrade button.

The upgrade to 1.2.0 sets the accounts, the analytic account and the tax of the salary rules per
company: the value of a rule is kept for the companies that can use it (the companies of the account
and their branches), and only for the company of the rule when it has one.

The upgrade to 1.2.3 checks the companies of the salary journals, analytic accounts and taxes of the
contracts, payslips, batches and salary rules: they belong to the company of the record. Nothing is
changed by the upgrade: the records already linking another company are listed as warnings in the
server log, and the next change of such a record asks to fix its link first.

Configuration
=============

Set the debit and credit accounts of the salary rules in Payroll > Configuration > Salary Rules, on the
Accounting tab of each rule. The analytic account and the tax of the rule are optional.

Make sure the company has a miscellaneous journal with a default account, so that the payslips have a
salary journal and the adjustment line can be posted. A different journal can be set on the employee
contract, on the payslip or on the payslip batch.

To pay the salaries from the payslips, give the net salary rule a credit account that allows
reconciliation, e.g. a payable account, and give the employees a contact. Paying needs the Invoicing
rights of Accounting.

Usage
=====

Create a payslip in Payroll > Employee Payslips, or a batch in Payroll > Payslips Batches and generate
the payslips of the employees. Check the salary journal and the accounting date, compute the payslip and
confirm it: the journal entry is created and posted, and is available from the payslip.

Then click Register Payment on the payslip, or Register Payments on the batch, choose the journal and
the date, and click Create Payments.

Dependencies
============

* Odoo 20 HR Payroll (``om_hr_payroll``)
* Invoicing (``account``)

Support
=======

Odoo Mates, odoomates@gmail.com

Contributors: Odoo Mates <odoomates@gmail.com>, Odoo SA.
