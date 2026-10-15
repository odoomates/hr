==================
Payroll Bank Files
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Export the salary transfers of the payslips as the file your bank asks for,
with File Layouts.

Features
========

* Export Bank File on a payslip batch or on a payslip, or Export: followed by
  the name of the layout in the Action menu of the payslips selected: the
  confirmed payslips only, without the refunds.
* One line per salary transfer: the net salary split over the bank accounts of
  the employee by their Salary Distribution (fixed amounts and percentages), the
  last account taking what the rounding leaves. An employee without a
  distribution is paid on their main bank account.
* The columns read ``payslip``, ``employee``, ``partner``, ``bank``,
  ``amount``, ``net``, ``batch``, ``company``, ``currency``, ``period_from``
  and ``period_to``, and ``line('BASIC')`` for the total of any salary rule, as
  the WPS files ask.
* The problems before sending: an employee without a bank account, an account
  not trusted for payments, a payslip already in another bank file.
* Each payslip shows the bank files it is in (In a Bank File, Bank Files), and
  every file is kept in Payroll > Bank Files to download it again.
* Bank Transfer (CSV) to start with; copy it into the layout of your bank in
  Payroll > Configuration > Bank File Layouts.

Configuration
=============

Payroll managers set up the layouts in Payroll > Configuration > Bank File
Layouts: start from a copy of Bank Transfer (CSV) and change its format and its
columns to the ones of your bank. The Salary Distribution and the bank accounts
of the employees, and whether an account is trusted for payments, come from the
employee and the contact.

Usage
=====

#. Confirm the payslips, alone or in a batch.
#. Click Export Bank File on the batch or on the payslip, or select payslips in
   their list and choose Export: Bank Transfer (CSV), or your own layout, in
   the Action menu.
#. Choose the layout, check the preview and the problems, then click Download.
#. Find the files again in Payroll > Bank Files.

Dependencies
============

* File Layouts (``om_file_layout``)
* Odoo 20 HR Payroll (``om_hr_payroll``)

Support
=======

Odoo Mates, odoomates@gmail.com
