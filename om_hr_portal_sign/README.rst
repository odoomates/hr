=====================
HR Portal: Policies
=====================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The policies of HR Sign on the website portal, for the employees without a backend user.

Features
========

* A Policies card on ``/my/hr``.
* ``/my/hr/policies``: the policies asked to the employee, those to answer first, with their due dates.
* ``/my/hr/policies/<id>``: the text or the PDF of the version; I Have Read and Agree answers it, or Sign opens
  the signing page of the policies to sign.
* The emails of the policies lead the portal employees to their page.
* Each employee reaches only the policies asked to them: any other address answers Not Found.

Usage
=====

Grant the portal to the employee (Employees > the employee > Grant Portal Access); they find their policies in
My Account > My HR > Policies, and the documents to sign in My Account > Signatures.

Dependencies
============

* ``om_hr_portal``, ``om_hr_sign``. Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
