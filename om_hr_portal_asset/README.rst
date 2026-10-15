===================
 HR Portal: Assets
===================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Shows the employees the laptops, phones and tools of the company in their hands, on the website portal.

Features
========

* An **Assets** card on My HR opens ``/my/hr/assets``: each assignment of the employee, with the asset,
  the serial number, the date handed over, the date returned and the status (returned, lost...).
* Read only: HR hands over and takes back the assets in the backend.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

The employee opens **My HR > Assets** on the portal.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_asset`` (HR Assets)

Installs by itself with HR Portal and HR Assets.

Support
=======

Odoo Mates, odoomates@gmail.com
