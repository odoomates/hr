===============
HR Pre-boarding
===============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

New hires get ready before their first day on the website: they give their details to HR, who reviews them
before they are written on the employee, and they read what to know for their first day.

Features
========

* Start Pre-boarding on an employee whose contract starts soon: the new hire gets a portal access, if they have
  no user yet, and a welcome email.
* The steps of the company, asked to all the new hires or to some departments, job positions or tags:

  * Personal Details: private address, phone and email, birth date and place, nationality, gender, marital
    status, spouse and children;
  * Emergency Contact;
  * Bank Account, for the salary: created on the work contact of the employee;
  * ID Numbers: identification, passport, visa and work permit numbers;
  * Read: a page to read, e.g. the first day;
  * Task: something to do, confirmed by the new hire.

* HR reviews the details given: the values the employee has now next to those given, then Apply writes them on
  the employee, or Send Back asks the new hire to correct them with a note. A field left blank keeps what the
  employee has.
* The welcome page of the new hire shows their progress, their steps, the first day information and their buddy
  (the manager by default).
* HR follows the new hires in Employees > Pre-boarding: progress, what to review, and an activity for each
  answer to review.
* Optionally, an onboarding plan of the employees is launched when the pre-boarding starts, e.g. to prepare the
  laptop.
* The pre-boarding closes on the first day; the employee keeps their portal access, and HR may invite them as a
  user of the backend.
* With the bridges: documents to upload (HR Pre-boarding: Documents), policies to agree to and documents to
  sign (HR Pre-boarding: Sign), and a start on its own from accepted job offers (HR Pre-boarding: Job Offers).

Configuration
=============

* Employees > Configuration > Pre-boarding Steps: the steps, ready-made ones included.
* Employees > Configuration > Settings > Pre-boarding: the first day information and the onboarding plan.

Usage
=====

* On the employee form, Start Pre-boarding.
* The new hire follows the link of the welcome email, then My Account > My HR > Welcome.
* Review their answers from Employees > Pre-boarding.

Dependencies
============

* ``om_hr_portal``.

Support
=======

Odoo Mates, odoomates@gmail.com
