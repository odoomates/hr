=============
HR Job Offers
=============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Job offers made from the applicant, approved, signed by the company and the candidate through Sign, and turned
into the contract of the new employee.

Features
========

* New Offer on the applicant: job position, department, monthly wage, start date, employee type, working
  schedule, end of probation, other benefits and the date the offer is valid until; prefilled from the
  applicant (proposed or expected salary, availability).
* Approval before sending, along an approval flow you change in Approvals (HR managers by default; e.g. the
  department manager first, or only above a wage).
* Send for Signature issues the Offer Letter (an editable print template with the terms) and sends it through
  Sign: the person sending signs first for the company, then the candidate countersigns from a link sent by
  email, without an account.
* The offer expires with its signature request on its Valid Until date; a recruiter can withdraw a sent offer.
* Accepted, the applicant moves to the hired stage with the salary and the availability of the offer; Create
  Employee fills the contract of the new employee: wage, start date, employee type, working schedule, end of
  probation, job and department.
* Declined offers keep the reason given by the candidate; New Offer from This One starts again from a refused,
  declined, expired or cancelled offer.

Configuration
=============

* Adapt the Offer Letter in Print Templates > Templates (its text, signers and the email code option).
* Change who approves the offers in Approvals > Configuration > Approval Flows > Job Offers.

Usage
=====

* Open an applicant, New Offer, fill the terms and Submit for Approval.
* Once approved, Send for Signature, then sign the letter from Sign > To Sign.
* Recruitment > Applications > Offers lists the offers and their status.

Dependencies
============

* Recruitment (``hr_recruitment``), ``om_sign``, ``om_approval``.

Support
=======

Odoo Mates, odoomates@gmail.com
