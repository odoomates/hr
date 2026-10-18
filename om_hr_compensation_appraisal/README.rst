==============================
HR Compensation: Appraisals
==============================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Links HR Compensation with HR Appraisals: the merit cycles show the last rating
of each employee and suggest their raise from a merit matrix.

Features
========

* Each line of a merit cycle shows the rating of the last appraisal done of the
  employee.
* The **merit matrix** gives the raise suggested for each rating by where the
  wage sits in its band: a better rating gets more, and a wage already high in
  its band gets less, so that the wages move towards the midpoint. Generating a
  merit cycle fills each proposal with it; the managers then adjust them.
* A starting matrix is installed for the ratings of HR Appraisals, e.g. 5% for
  Exceeds Expectations in the lower third of the band. A company may have its
  own matrix, which wins over the shared one.

Configuration
=============

Employees > Configuration > Merit Matrix (HR administrators).

Dependencies
============

* HR Compensation (``om_hr_compensation``)
* HR Appraisals (``om_hr_appraisal``)

Installs by itself with both.

Support
=======

Odoo Mates, odoomates@gmail.com
