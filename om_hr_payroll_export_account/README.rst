============================
Payroll Bank Files: Payments
============================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Register the salary payments in Accounting at the moment you export the bank
file of the payslips, instead of paying them again by hand afterwards.

Features
========

* Register the Payments, an option of Export Bank File, with the Bank Journal
  (the first bank journal of the company by default) and the Payment Date.
* On Download, the payslips of the file still to pay are paid in Accounting, as
  Pay Salaries does: one payment per employee, matched with the net salary of
  the journal entry of the payslips.
* The payslips already paid, the refunds and the payslips without a posted
  entry are left out; the payment status of each payslip follows.

Configuration
=============

The option is shown to the users with the Accounting rights of Invoicing
(Billing) or more. The net salary rule needs a credit account that allows
reconciliation, as for Pay Salaries.

Usage
=====

#. Click Export Bank File on a confirmed payslip batch or payslip.
#. Tick Register the Payments, check the Bank Journal and the Payment Date.
#. Click Download: the file is exported and the payments are registered.

Dependencies
============

Installs by itself with Payroll Bank Files (``om_hr_payroll_export``) and
Odoo 20 HR Payroll Accounting (``om_hr_payroll_account``).

Support
=======

Odoo Mates, odoomates@gmail.com
