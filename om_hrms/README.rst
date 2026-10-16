=============
Odoo Mates HR
=============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

All the Odoo Mates HR modules in one download, for Odoo 20 Community, with or
without Accounting. The module adds nothing itself: it depends on each of them,
so that the App Store download holds them all and installing it installs them
all.

Features
========

What it installs:

* ``om_hr_base`` HR Base: what the HR modules share, the My HR menu and the
  employee category of the contract.
* ``om_approval`` Approvals: approval flows for any app. A button, e.g.
  Confirm on the sale orders above an amount, waits for the approval of users,
  groups or the user a field names, in steps, and runs once approved.
* ``om_hr_approval`` HR Approvals: the manager, the department manager, the
  coach or the HR responsible approve, and the employees send HR requests.
* ``om_hr_approval_leave`` HR Approvals: Time Off: an approver on validated
  time off is replaced by their substitute, else their manager.
* ``om_hr_payroll`` Payroll: salary structures, rules, components, parameters
  and brackets, payslips and payslip batches, paid on the working schedule or
  on the attendances.
* ``om_hr_loan`` HR Loans: loans and salary advances, approved along a flow
  and repaid in monthly installments.
* ``om_hr_loan_payroll`` HR Loans in Payroll: the installments due are
  deducted from the payslips.
* ``om_hr_exit`` HR Exit: resignations and terminations, approved along a
  flow, cleared by the people of a checklist during the notice period, then
  registered as the departure of the employee.
* ``om_hr_gratuity`` HR Gratuity: the end of service gratuity of an exit, from
  a scheme of days of pay per year of service and reasons of leaving.
* ``om_hr_exit_payroll`` HR Exit in Payroll: the final settlement payslip,
  with the unused time off paid out, the gratuity and the loans still due.
* ``om_document`` Document Expiry: documents with an expiry date kept on any
  record, reminders before they expire, and their renewal.
* ``om_hr_document`` HR Documents: the passports, visas, permits and IDs of
  the employees, on a Documents tab where files are dropped on cards.
* ``om_print_template`` Print Templates: certificates and letters written in
  the editor and printed from the Print menu of any record, numbered, kept as
  printed, with an optional verification QR code.
* ``om_print_template_document`` Print Templates: Documents: files a print as
  an expiring document of the record, e.g. an NOC valid for 30 days.
* ``om_sign`` Sign: prints and PDF files signed from an email link, in order,
  with a signature certificate.
* ``om_hr_sign`` HR Sign: documents signed by the employee and the manager, and
  the company policies read and agreed or signed, version after version.
* ``om_hr_recruitment_offer`` HR Job Offers: offers made from the applicant,
  approved, signed by the company and the candidate, and turned into the
  contract of the new employee (installs Recruitment).
* ``om_hr_preboarding`` HR Pre-boarding: new hires get ready before their first
  day on the website, their details reviewed by HR, with the bridges for
  documents to upload (``om_hr_preboarding_document``), policies and signatures
  (``om_hr_preboarding_sign``) and accepted job offers (``om_hr_preboarding_offer``).
* ``om_hr_certificate`` HR Certificates: salary, employment and experience
  certificates and NOC, requested by the employees and approved.
* ``om_hr_appraisal`` HR Appraisals: self assessment, manager review and
  rating, goals, probation reviews, planned appraisals and review cycles.
* ``om_hr_overtime_payroll`` Overtime in Payroll: the validated overtime of
  the Attendances app paid on the payslips, at the rate of each time rule. It
  installs Attendances.
* ``om_hr_overtime_request`` Overtime Pre-Approval: overtime authorised in
  advance; beyond it, the manager accepts or rejects it.
* ``om_hr_asset`` HR Assets: the assets in the hands of the employees, as the
  equipment of the Maintenance app, with handover forms and the history of who
  held each one. It installs Maintenance.
* ``om_hr_asset_exit`` HR Assets in Exits: an exit is cleared only once the
  assets of the employee are back.
* ``om_hr_asset_payroll`` HR Assets in Payroll: charges for assets lost or
  damaged deducted from the payslips.
* ``om_file_layout`` File Layouts: CSV, fixed width and Excel files designed
  column by column and exported from the Action menu of any record.
* ``om_hr_payroll_export`` Payroll Bank Files: the salary transfers of the
  payslips, split by the salary distribution, in the layout of your bank.
* ``om_hr_payroll_adjustment`` Payroll Adjustments: bonuses, commissions,
  fines and court deductions, once, for some months or until a total, fixed or
  a percentage, each type on its own payslip line.
* ``om_hr_lateness`` HR Lateness: late arrivals and early departures against
  the working schedule, grace minutes, a penalty matrix by minutes and by
  occurrence in the month, warnings and excuses.
* ``om_hr_lateness_payroll`` HR Lateness Payroll: the penalties of a month
  taken off the payslips as payroll adjustments.
* ``om_hr_shift`` Shifts: shift templates, a roster board, rotations, open
  shifts, swaps and availability, with warnings on time off, rest and weekly
  hours; published shifts are the working schedule of the employees.
* ``om_hr_shift_payroll`` Shift Allowances in Payroll: the allowance of each
  published shift paid on the payslips, e.g. a night shift allowance.
* ``om_hr_reminder`` HR Reminders: birthdays, work anniversaries and probation
  ends through the Automation Rules, and the celebrations of the month in
  My HR > Celebrations.
* ``om_hr_announcement`` HR Announcements: company, department and job position
  announcements, read in My HR and from the megaphone of the top bar, and
  acknowledged when asked.
* ``om_hr_portal`` HR Portal: employee self-service on the website, for the
  employees without a user of the backend, with the pages of:

  * payslips (``om_hr_portal_payslip``);
  * time off (``om_hr_portal_leave``);
  * loans (``om_hr_portal_loan``);
  * certificates (``om_hr_portal_certificate``);
  * documents (``om_hr_portal_document``);
  * assets (``om_hr_portal_asset``);
  * appraisals (``om_hr_portal_appraisal``);
  * resignation (``om_hr_portal_exit``);
  * pay adjustments (``om_hr_portal_adjustment``);
  * shifts (``om_hr_portal_shift``);
  * announcements (``om_hr_portal_announcement``);
  * policies (``om_hr_portal_sign``).

* ``om_spreadsheet_hr`` HR Dashboards, ``om_spreadsheet_hr_payroll`` Payroll
  Dashboard, ``om_spreadsheet_hr_time`` Time Off and Attendance Dashboard and
  ``om_spreadsheet_hr_talent`` Talent and Compliance Dashboard: the Workforce,
  Payroll, Time Off and Attendance, and Talent and Compliance dashboards of the
  Dashboards app, with the OM.HR spreadsheet formulas.

Every employee with a user, the light users of Odoo 20 included, has the My HR
app: their payslips, requests, loans, certificates, documents, assets,
appraisals, goals and exit.

With Accounting
===============

The bundle does not install Accounting. The accounting links are separate
modules, part of the same download:

* ``om_hr_payroll_account`` Payroll Accounting: the journal entries of the
  payslips and the salary payments. Installed from Payroll > Configuration >
  Settings > Payroll Entries; it installs Accounting.
* ``om_hr_loan_account`` HR Loans in Accounting: loans paid out and repaid as
  payments on a loan account, reconciled per employee. Installs by itself with
  HR Loans and Accounting.
* ``om_hr_loan_payroll_account`` HR Loans in Payroll Accounting: the
  installments deducted from the payslips repay the loan account. Installs by
  itself with the modules above.
* ``om_hr_payroll_export_account`` Payroll Bank Files: Payments: register the
  salary payments when exporting the bank file. Installs by itself with
  Payroll Bank Files and Payroll Accounting.

Usage
=====

Install Odoo Mates HR to install every module above. To use only some, add the
download to the addons folder and install the modules you need instead, e.g.
HR Loans alone; each installs what it depends on, and the bridges between two
modules (e.g. HR Loans in Payroll) install by themselves once both are there.

Dependencies
============

* Odoo 20.0 Community Edition.
* No external Python library and no paid Odoo Enterprise module.
* The Odoo Mates HR modules listed above, and through them the Community apps
  Employees, Time Off, Attendances, Maintenance, Work Entries, Portal,
  Dashboards and Automation Rules.

Support
=======

Odoo Mates, odoomates@gmail.com
