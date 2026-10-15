===========
 HR Portal
===========

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Employee self-service on the website portal: the employees reach their HR from a phone or a computer,
without being users of the backend.

Features
========

* **Grant Portal Access** on the employee form (HR officers) creates a portal user for the employee,
  with the work email (or the private email) as login, and emails them an invitation to set their
  password. It refuses when the employee already has a user, when the email is the login of a backend
  user, or when that portal user already belongs to another employee.
* A **My HR** card on the portal home (``/my``) opens ``/my/hr``: the photo, job and department of the
  employee, and a card per HR page installed.
* **My Profile** (``/my/hr/profile``): job, department, manager, joining date, work email and phones,
  company. It is read only; the employee tells HR what to correct.
* The pages of the HR modules come from small bridge modules that install by themselves with the HR
  module they serve: payslips, time off, loans, certificates, documents, assets, appraisals,
  resignation, pay adjustments and shifts.
* Each page shows only what belongs to the employee logged in: changing an id in the address gives a
  page not found, not someone else's record.

Configuration
=============

Only HR officers (group ``hr.group_hr_user``) see and use **Grant Portal Access**. An employee
already linked to a user reaches ``/my/hr`` with that user.

Usage
=====

#. Set the work email of the employee.
#. On the employee form, click **Grant Portal Access** and confirm.
#. The employee follows the link of the invitation email, sets a password and finds **My HR** on the
   portal.

Dependencies
============

* ``portal``
* ``om_hr_base`` (HR Base)

Support
=======

Odoo Mates, odoomates@gmail.com
