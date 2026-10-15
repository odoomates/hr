=======================
 HR Portal: Appraisals
=======================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees fill in their self assessment and keep their goals up to date on the website portal.

Features
========

* An **Appraisals** card on My HR opens ``/my/hr/appraisals``: the appraisals of the employee (cancelled
  ones left out) with the deadline, the status and the rating, and their goals.
* Each goal shows its progress; the employee sets a new progress from 0 to 100 and clicks **Update**.
* ``/my/hr/appraisals/<id>``: the deadline and the meeting date. While the appraisal waits for the self
  assessment, the employee writes it: **Save** keeps it, **Submit to My Manager** sends it on.
* The review of the manager shows once the appraisal is done.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

#. The employee opens **My HR > Appraisals** and clicks the appraisal.
#. They write their self assessment, save it as often as needed, then submit it.
#. On the list, they update the progress of their goals.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_appraisal`` (HR Appraisals)

Installs by itself with HR Portal and HR Appraisals.

Support
=======

Odoo Mates, odoomates@gmail.com
