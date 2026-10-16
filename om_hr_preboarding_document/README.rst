==========================
HR Pre-boarding: Documents
==========================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

New hires upload their passport, ID, visa or permits as steps of their pre-boarding.

Features
========

* An Upload a Document step, of a document type of the employees (e.g. Passport).
* When the pre-boarding starts, the document waits in the documents of the employee; the new hire uploads the
  file from their documents page on the website.
* The step is done once a file is uploaded; HR checks the document in HR Documents as usual.

Configuration
=============

Employees > Configuration > Pre-boarding Steps: add a step Upload a Document and choose its document type.

Dependencies
============

* ``om_hr_preboarding``, ``om_hr_portal_document``. Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
