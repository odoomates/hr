=====================
 HR Portal: Payslips
=====================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees read their payslips and download them on the website portal.

Features
========

* A **Payslips** card on My HR opens ``/my/hr/payslips``: the payslips of the employee once they are
  done, the newest first, with the period and the net. Refunds are not listed.
* ``/my/hr/payslips/<id>``: the lines that appear on the payslip, the net in bold.
* **Download PDF** gives the payslip report through ``/my/payslip/<id>/pdf`` of the payroll, for the
  employee it belongs to only.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

The employee opens **My HR > Payslips**, clicks a payslip to read it, and downloads the PDF.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_payroll`` (Odoo 20 HR Payroll)

Installs by itself with HR Portal and Odoo 20 HR Payroll.

Support
=======

Odoo Mates, odoomates@gmail.com
