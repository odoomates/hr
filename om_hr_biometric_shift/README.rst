=====================================
Biometric Attendance Machine - Shifts
=====================================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The punches of the biometric devices read against the published shifts. It
installs by itself with *Biometric Attendance Machine - ZKTeco, eSSL, Fingerprint, Face* and *Shifts*.

Features
========

* A punch that alternates (Alternate mode, or no known status) checks in near
  the start of the employee's shift and checks out near its end. A missed
  check-in stays a check-out without check-in, to correct, instead of turning
  the check-ins and check-outs of the next days around.
* A check-in from before the shift, not checked out when the next shift starts,
  is a forgotten check-out: closed and flagged *To Review*, even when it is
  shorter than the maximum shift. Night shifts work the same way.
* Without a published shift around the punch, the punches alternate as usual.

Dependencies
============

* ``om_hr_biometric`` (Biometric Attendance Machine)
* ``om_hr_shift`` (Shifts)

Support
=======

Odoo Mates, odoomates@gmail.com
