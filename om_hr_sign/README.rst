=======
HR Sign
=======

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The employees sign their documents through Sign, and read and agree to the policies of the company, or sign
them.

Features
========

* Print templates of the employees name who signs among the employee, their manager, their coach or any
  employee field, e.g. a contract signed by the employee and then by the manager. The employee signs as their
  work contact.
* Request Signature on the employee form sends any PDF, the employee suggested as signer; the Signatures smart
  button lists the requests about the employee and those they sign.
* HR officers send documents for signature and read the signature requests concerning employees.
* Policies, e.g. the code of conduct, the IT use or an NDA: their text written in the editor or uploaded as a
  PDF, version after version.
* Each policy is answered by Read and Agree (one click, logged with the date, the user and the IP address) or by
  a signature through Sign (signed PDF and certificate).
* A policy is asked to the whole company, departments (with their sub-departments), job positions, employee
  tags or some employees, with a due date and reminders.
* Publishing a new version asks everyone again; the answers to the previous versions stay.
* New employees, and those moving into the audience of a policy, e.g. to a department, are asked the current
  version (Ask New Employees).
* HR follows who answered: answered / asked on the policy, the answers by department, the overdue ones, Ask
  Again for an employee who declined to sign or whose request expired.
* My HR > My Policies and My HR > My Signatures for the employees.

Configuration
=============

* Employees > Policies > Policies: create the policy, its answer, its employees, then New Version to write its
  text or upload its PDF, and Publish.

Usage
=====

* The employees get an email and answer in My HR > My Policies (or on the portal with HR Portal: Policies).
* HR follows the answers in Employees > Policies > Policy Answers.

Dependencies
============

* ``om_sign``, ``om_hr_base``.

Support
=======

Odoo Mates, odoomates@gmail.com
