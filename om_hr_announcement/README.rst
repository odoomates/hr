==================
HR Announcements
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Tell the whole company, a department or a team what they should know, and see who read it and who
acknowledged it.

Features
========

* Announcements with a title, a formatted message and attachments, in Employees > Announcements.
* Audience: the whole company, departments (their sub-departments included), job positions, employee tags or
  chosen employees; the number of employees reached is shown before publishing.
* Shown from a date and until another: published at once or scheduled, then expired.
* Important announcements come first and are highlighted.
* Each employee gets the announcement in their inbox, or by email as they prefer.
* Employees read their announcements in My HR > Announcements and from the megaphone of the top bar, which
  counts what waits for them; opening an announcement marks it read.
* Requires Acknowledgement: each employee confirms they have read and understood it.
* The authors follow the read and acknowledged rates and the list of the employees still pending; Remind
  Pending notifies them again, or automatically after a number of days.
* Employees > Announcements > Announcement Report: read and acknowledged by department.

Configuration
=============

* HR officers publish to anyone.
* A department manager publishes to the departments they manage, and their sub-departments, only.
* A cron job publishes the scheduled announcements, expires the ended ones and sends the automatic reminders,
  every hour.

Usage
=====

#. Employees > Announcements > New: write the title and the message, choose the audience, the dates, and
   whether it requires an acknowledgement.
#. Publish: the employees reached are notified, now or on the day it shows from.
#. Follow the Read and Acknowledged buttons of the announcement; Remind Pending when needed.

Dependencies
============

* ``om_hr_base``, ``mail``.
* With ``om_hr_portal``, *HR Portal: Announcements* installs by itself and brings the announcements to the
  website portal.

Support
=======

Odoo Mates, odoomates@gmail.com
