============
HR Documents
============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The documents of the employees, such as passports, visas, work permits and
IDs, with their number, their dates and their files, and reminders before they
expire. Built on Document Expiry (``om_document``).

Features
========

* A Documents tab on the employee: a card per document, coloured by how close
  it is to expiring, and a card per document type the employee has no document
  of yet. Drop a file on a card to attach it, or on a missing card to create
  the document. A warning shows how many documents are expiring or expired,
  and a Documents smart button lists them.
* Passport, National ID, Residence / Visa, Work Permit and Driving License
  types to start with, and your own in Employees > Configuration > Employee >
  Document Types.
* Reminders go to the HR responsible of the contract of the employee, else to
  the HR managers of the company. A type can also email the employee.
* The number of a Passport or a National ID also fills the matching field of
  the employee.
* Employees see their own documents in My HR > My Documents; HR officers
  manage all the documents of the employees.
* Employees > Documents > Expiring and Expired list what needs renewing; All
  Documents lists them all, with filters and groups by employee and
  department.

Configuration
=============

* HR managers adjust the document types and their reminder days in Employees >
  Configuration > Employee > Document Types.
* Set the HR responsible on the contracts of the employees: they receive the
  reminders.

Usage
=====

* Open an employee, go to the Documents tab and drop the scanned files on the
  cards, then fill in the number and the dates.
* Follow Employees > Documents > Expiring, and renew a document from its form
  when the new one arrives.

Dependencies
============

* Document Expiry (``om_document``)
* HR Base (``om_hr_base``)

Support
=======

Odoo Mates, odoomates@gmail.com
