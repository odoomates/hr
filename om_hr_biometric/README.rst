==============================================================
Biometric Attendance Machine - ZKTeco, eSSL, Fingerprint, Face
==============================================================

For Odoo 19 Community, by `Odoo Mates <https://github.com/odoomates/hr>`_.

The punches of the ZKTeco and eSSL biometric devices become the check-ins and
check-outs of the employees.

Features
========

* **ADMS (push)**: the device sends its punches to Odoo over HTTP as they
  happen, and collects the commands of Odoo. No fixed IP address and no
  program on a computer of the office. No external Python library.
* Every punch is kept as the device sent it, once, then processed into the
  attendances employee by employee, in the order of time, in the timezone of
  the device (summer time included).
* **Modes** per device: *Alternate* (a punch checks in, the next one checks
  out), *Status Codes* (the status selected on the device: check in, check out,
  break, overtime; a punch without a known status alternates), *Check-In Only*
  and *Check-Out Only* for separate entry and exit devices.
* Repeated punches within a minute are ignored. A forgotten check-out never
  blocks the employee: past the maximum shift, the open attendance is closed at
  its check-in and flagged *To Review*, and the punch starts a new attendance.
* Punches of an unknown user wait, and are processed as soon as the user is
  linked to an employee. No employee is ever created by a device.
* **Device users**: the devices send their users, linked to the employees by
  their *Biometric ID*. Employees are sent to the devices from Odoo, or removed
  from them. One employee can be on several devices.
* Download the punches of a period again, restart a device, set its clock, read
  its information.
* **Fingerprints**: start the enrollment of a finger from Odoo; copy a user to
  other devices with its fingerprints, so the employee does not enroll again.
* **Biometric templates** are kept in Odoo only when the company chooses to
  (off by default), to copy users over ADMS; only the attendance managers see
  them, and one click deletes them from Odoo.
* *Process Again* a period, e.g. after a change of mode: the attendances of the
  devices are made again, those entered by hand are kept.
* **Daily Biometric Attendance**: first and last punch of each employee per
  day; the punches by device, day and kind of verification.
* **Attendance Status**: each day of each employee against the working
  schedule, the time off and the public holidays: on time, late, left early,
  late and left early, missing check-out, absent, on time off, worked on a day
  off, with a tolerance in minutes. In list, pivot and graph; *Absences* shows
  the absent days only.
* **Monthly Attendance Sheet** in PDF (A4 landscape): one line per employee,
  one letter per day, with the days worked, absences, late arrivals and hours.
* **Today**: a board of who is at work, late, not arrived yet or absent.
* **Devices dashboard**: each device online or not, its last contact, punches
  of the last 24 hours, users linked to an employee or not. *Biometric Device
  Health* lists the unknown users, punches in error and failed commands.
* **Offline alerts**: when a device stops calling (30 minutes by default), its
  responsible gets an activity, notified by email or in Odoo as they chose; it
  is marked done by itself when the device is back.
* A **setup checklist** on each new device: reach it, read its information,
  link its users, receive the first punches.
* Device users are linked to the employees by their *Biometric ID*, else by
  their name, the same without accents, or the start of the name (the devices
  keep 24 characters); a name shared by several employees is left to link by
  hand. *Map Employees* links those left.
* Employees are sent to the devices with the fingerprints they enrolled on
  another device, so they do not enroll again.
* Device commands done or failed are deleted after 180 days.
* The reports are in Attendances > Management > Biometric.
* Attendances from the devices show their device and the *Biometric Device*
  mode; lateness, overtime and the payslips read them like any attendance.
* Multi-company: each device and its punches belong to a company.

Configuration
=============

Two ways to connect a device, chosen device by device:

* **ADMS (push)**, in this module: the device sends its punches to Odoo over
  HTTP. No fixed IP address, no port to open. Look for *Cloud Server Setting*
  (or *ADMS*) in Menu > Communication on the device.
* **TCP (pull)**, with *Biometric Attendance Machine - TCP/UDP* (``om_hr_biometric_zk``):
  Odoo reads the device at its IP address on port 4370. For the devices
  without ADMS, or on a network they cannot leave.

A device with ADMS
------------------

#. Attendances > Configuration > Biometric Devices: create the device with its
   serial number (on the device, Menu > System Info > Device Info), its
   timezone and its mode (*Alternate* when the employees choose no status).
#. On the device, Menu > Communication > Cloud Server Setting: the domain name
   of Odoo as server address (or its IP address on the local network), port
   443 with HTTPS (8069 for an Odoo on the local network). Enable *Domain
   Name* for a domain name, and *HTTPS* with port 443.
#. Within a minute the device shows *Online* in Odoo. Punch once: the punch is
   in Attendances > Management > Biometric > Punches.

The devices call fixed URLs (``/iclock/...``): with several databases on the
server, the domain name must select the database (``dbfilter``). Behind a
proxy, keep HTTPS and allow only the IP addresses of the devices (*Allowed IP
Addresses*): ADMS has no password of its own.

A device over TCP
-----------------

#. Install *Biometric Attendance Machine - TCP/UDP* (``om_hr_biometric_zk``).
#. On the device: a fixed IP address (Menu > Communication > Ethernet) and the
   communication key (Menu > Communication > PC Connection, 0 when none).
#. The Odoo server must reach the device on port 4370: same network, VPN or a
   port forwarded by the router.
#. Create the device with the *TCP (Pull)* protocol, its IP address, port and
   communication key, then *Test Connection*. Odoo downloads the new punches
   every 10 minutes, or at once with *Download Now*.

Then, for all the devices
-------------------------

#. Give the employees a *Biometric ID* (the user ID on the device, employee
   form, HR Settings tab), or send them from Odoo with *Send Employees*: those
   without one get the next free number.
#. Attendances > Configuration > Settings > Biometric Devices: the maximum
   shift, the tolerance of the attendance status, when a device is offline,
   and whether Odoo keeps the biometric templates (off by default).
#. On each device: its *Responsible* for the offline alerts.

Usage
=====

#. Employees punch on the devices; their attendances follow within seconds.
#. The attendance managers check Attendances > Management > Biometric >
   Punches for unknown users and errors, and the attendances *To Review*.

Dependencies
============

* ``hr_attendance``

Support
=======

Odoo Mates, odoomates@gmail.com
