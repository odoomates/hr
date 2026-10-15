====================
HR Assets in Payroll
====================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Links HR Assets to Payroll: what an employee is charged for an asset returned
damaged or reported lost comes off their salary.

Features
========

* The Asset Charges salary rule (code ``ASSET``, a deduction) deducts the
  charges of the employee: those up to the end of the period of the payslip
  that are not deducted yet, or all of them on the final settlement of an exit
  (with HR Exit in Payroll).
* The charges are read when the payslip is computed, as the input ``ASSET``.
* Each charge is deducted once, and again only if its payslip is cancelled or
  refunded. The assignment shows the payslip it was deducted on (Deducted On,
  for the payroll officers).

Configuration
=============

On install, the rule is added to the Base for new structures structure, so
the structures created from then on deduct the charges. Add the rule
(Asset Charges) to your own salary structures that should deduct them.

Usage
=====

#. Set a Charge to Employee when you return an asset as damaged or report it
   lost.
#. Compute the next payslip of the employee: the charge is on the Asset
   Charges line.

Dependencies
============

Installs by itself with HR Assets (``om_hr_asset``) and Payroll
(``om_hr_payroll``).

Support
=======

Odoo Mates, odoomates@gmail.com
