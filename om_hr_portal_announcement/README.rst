==========================
HR Portal: Announcements
==========================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The announcements of HR Announcements on the website portal, for the employees without a backend user.

Features
========

* An Announcements card on ``/my/hr``.
* ``/my/hr/announcements``: the published announcements addressed to the employee, the important and the
  unread ones first, with their status (Unread, To Acknowledge, Acknowledged).
* ``/my/hr/announcements/<id>``: the message and its attachments; opening it marks it read.
* I Have Read and Understood: acknowledges the announcement when it asks for it.
* Each employee sees only the announcements addressed to them: any other address answers Not Found.

Usage
=====

Grant the portal to the employee (Employees > the employee > Grant Portal Access); they find their
announcements in My Account > My HR > Announcements.

Dependencies
============

* ``om_hr_portal``, ``om_hr_announcement``. Installs by itself with them.

Support
=======

Odoo Mates, odoomates@gmail.com
