=========================
 HR Portal: Certificates
=========================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees ask for their certificates (salary, employment, experience, NOC...) and download
them on the website portal.

Features
========

* A **Certificates** card on My HR opens ``/my/hr/certificates``.
* **Ask for a Certificate**: the employee chooses the certificate, gives the addressee and the purpose,
  and sends the request, which is submitted for approval as from the backend.
* The list of their requests shows the certificate, the addressee, the date asked and the status.
* Once the certificate is issued, the **PDF** button downloads it
  (``/my/hr/certificates/<id>/pdf``).
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Configuration
=============

Only the certificate templates on employees with **Employees Can Request** ticked are offered,
those of no company or of the company of the employee (Employees > Configuration >
Certificate Templates).

Usage
=====

#. The employee opens **My HR > Certificates**, chooses a certificate and sends the request.
#. Once HR has approved and issued it, they download the PDF from the same page.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_certificate`` (HR Certificates)

Installs by itself with HR Portal and HR Certificates.

Support
=======

Odoo Mates, odoomates@gmail.com
