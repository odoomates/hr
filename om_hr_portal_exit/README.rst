========================
 HR Portal: Resignation
========================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Lets the employees hand in their resignation and follow their exit on the website portal.

Features
========

* A **Resignation** card on My HR opens ``/my/hr/resignation``.
* **Hand In My Resignation**: the date the notice is given, a note, and a box to tick to confirm. The
  exit is created and submitted for approval; an employee with an exit already in progress cannot hand
  in a second one.
* While the exit is in progress: its status, the notice date, the last working day, the step it waits
  for, and each clearance line, done or pending.
* Each employee sees only their own records: changing an id in the address gives a page not found,
  not someone else's record.

Usage
=====

#. The employee opens **My HR > Resignation**, fills in the form, ticks the box and confirms.
#. They come back to the same page to follow the approval and the clearance.

Dependencies
============

* ``om_hr_portal`` (HR Portal)
* ``om_hr_exit`` (HR Exit)

Installs by itself with HR Portal and HR Exit.

Support
=======

Odoo Mates, odoomates@gmail.com
