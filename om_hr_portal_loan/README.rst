==================
 HR Portal: Loans
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees ask for loans and salary advances and follow their repayment on the website portal.

Features
========

* A **Loans** card on My HR opens ``/my/hr/loans``.
* **Ask for a Loan**: the type, the amount, the number of installments (always one for a salary
  advance), the first month and the reason. The loan is created and submitted for approval.
* The list of their loans with the type, the date asked, the amount, the amount still due and the
  status.
* ``/my/hr/loans/<id>``: the detail of one loan and each monthly installment with its status.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

#. The employee opens **My HR > Loans**, fills in the form and sends the request.
#. They follow the approval, then the repayment, on the page of the loan.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_loan`` (HR Loans)

Installs by itself with HR Portal and HR Loans.

Support
=======

Odoo Mates, odoomates@gmail.com
