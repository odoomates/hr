==================
HR Pulse Surveys
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Anonymous pulse surveys of the employees, with the eNPS: a few questions every
few weeks, answered through one-time links that never tell who answered.

Features
========

* **Pulse surveys** on the Surveys application: a Pulse Survey is installed
  (the eNPS question from 0 to 10, three statements from 1 to 5 and an open
  question); change it, or pick any other survey.
* **Truly anonymous**: launching a pulse sends each employee their own one-time
  link by email. The link opens a ballot that knows the department of the
  employee, never the employee: the invitations hold who was asked, the ballots
  hold the answers, and nothing links one to the other. The ballots are created
  in a random order and only the hash of each link is stored; the invitation
  emails are deleted once sent. Not even an administrator can tell who answered
  what, so there are no reminders per person either.
* **Results by department, from five answers**: the eNPS, the average of each
  statement and the comments, sorted, for everyone and for each department.
  The departments with fewer than five answers are pooled and shown together
  from five answers; else they are left out of every result, Everyone
  included, since comparing Everyone with the departments shown would tell what
  they answered.
* **eNPS**: the share of promoters (9 and 10) less the share of detractors (0 to
  6), from -100 to 100. Each pulse keeps its participation and eNPS when it
  closes, for the trend over time (graph view).
* **Repeating pulses**: every N weeks, the next pulse is created when one closes
  and launched on its start date; a daily job closes the pulses whose deadline
  passed.

Usage
=====

#. Employees > Pulse Surveys (HR officers): create a pulse, choose the
   departments (or all), its deadline and how often it repeats, and Launch.
#. The employees answer from the email.
#. Read the Results tab while it runs; the pulse closes on its own after the
   deadline.

Dependencies
============

* HR Base (``om_hr_base``)
* Surveys (``survey``)

Support
=======

Odoo Mates, odoomates@gmail.com
