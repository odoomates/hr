===============
HR Certificates
===============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Salary, employment and experience certificates and No Objection Certificates,
requested by the employees, approved, and printed on the company letterhead.
Built on Print Templates (``om_print_template``) and HR Approvals
(``om_hr_approval``).

Features
========

* Employees ask for a certificate in My HR > My Certificates, with who it is
  for and why. Their manager, then the HR managers, approve it along an
  approval flow; a refusal carries its reason.
* Once approved, the certificate is printed from its template, numbered, and
  the employee is told and downloads it. The text is kept as printed.
* Salary Certificate, Employment Certificate, Experience Certificate and No
  Objection Certificate to start with; HR managers edit them, or add their own,
  in Employees > Configuration > Employee > Certificate Templates. Employees
  Can Request decides which ones employees ask for.
* HR also prints any certificate from the Print menu of an employee; a
  Certificates smart button on the employee lists what was issued.
* Employees > Certificates: To Approve, All Requests and Issued Certificates.
* A template can carry a verification QR code, and can file each certificate
  as a document of the employee, e.g. an NOC valid for 30 days, when Document
  Expiry is installed.
* Employees see their own requests and certificates only; HR managers cancel
  an issued certificate.

Configuration
=============

* Adjust the templates, their text, signatory and signature in Employees >
  Configuration > Employee > Certificate Templates.
* Change who approves in Employees > Configuration > Requests > Approval
  Flows, flow Certificates: by default the manager of the employee, then the
  HR managers; the employee does not approve his own request.

Usage
=====

* The employee creates a request in My HR > My Certificates, chooses the
  certificate and the addressee, and submits it.
* The approvers find it in Employees > Certificates > To Approve, or in My HR >
  To Approve, and approve or refuse it.
* Once approved, the employee opens the request and clicks Download.

Dependencies
============

* Print Templates (``om_print_template``)
* HR Approvals (``om_hr_approval``)

Support
=======

Odoo Mates, odoomates@gmail.com
