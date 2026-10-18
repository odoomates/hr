==============================
HR Appraisals: 360 Feedback
==============================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Peers, direct reports, the manager or anyone else answer a survey about the
employee of an appraisal; the employee reads the answers combined, without the
names.

Features
========

* **Ask for 360 Feedback** on an appraisal, for its manager and HR: choose how
  the reviewers work with the employee (manager, peer, direct report or other),
  pick them (the other reports of the manager are suggested as peers) and send.
  Each reviewer gets their own link to the survey by email.
* A **360 Feedback** survey is installed: three scales from 1 to 5 (quality of
  the work, working together, communication) and two open questions. Change it,
  or pick any other survey when asking.
* The **360 Answers** button shows who was asked and who answered.
* The **360 Feedback** tab of the appraisal combines the answers: the average of
  each scale, the count of each choice and the texts, sorted so that their order
  does not follow the reviewers.
* The employee reads the combined answers once the appraisal is done and at
  least three people answered, and never the names. The manager and HR also
  read who answered what. This holds through the API too: the employee cannot
  read the requests.

Configuration
=============

Install it from Employees > Configuration > Settings > Appraisals > 360
Feedback. Change the questions in Surveys > 360 Feedback.

The answers are survey answers: the users of the Surveys application read them
there with the names. Give the Surveys rights to HR only.

Usage
=====

#. On an appraisal under way, click Ask for 360 Feedback, choose the reviewers
   and send.
#. The reviewers answer from the email.
#. The manager reads the answers in the 360 Feedback tab; the employee reads the
   combined answers once the appraisal is done.

Dependencies
============

* HR Appraisals (``om_hr_appraisal``)
* Surveys (``survey``)

Support
=======

Odoo Mates, odoomates@gmail.com
