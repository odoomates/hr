===========================
HR Pre-boarding: Job Offers
===========================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The pre-boarding of a new hire starts by itself when HR creates the employee from an accepted job offer.

Features
========

* A setting of the company, Start From Accepted Offers.
* Create Employee on an applicant with an accepted offer then starts the pre-boarding, on the start date of the
  offer: the new hire gets their portal access and the welcome email.
* When it cannot start, e.g. the new hire has no email, the employee is created all the same and a note on the
  employee says why.

Configuration
=============

Employees > Configuration > Settings > Pre-boarding: tick Start From Accepted Offers.

Dependencies
============

* ``om_hr_preboarding``, ``om_hr_recruitment_offer``. Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
