======================
 HR Portal: Documents
======================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Shows the employees their passports, visas, permits and IDs with their expiry, and lets them send the
renewed files, on the website portal.

Features
========

* A **Documents** card on My HR opens ``/my/hr/documents``: a card per document of the employee, with
  the type, the number, the expiry date (coloured when it is expiring or expired) and the files to
  download.
* **Send**: the employee uploads the renewed passport or permit. The file is added to the document, a
  message is posted on it, and HR checks it and updates the dates.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

#. The employee opens **My HR > Documents**.
#. On a document to renew, they choose the new file and click **Send**.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_document`` (HR Documents)

Installs by itself with HR Portal and HR Documents.

Support
=======

Odoo Mates, odoomates@gmail.com
