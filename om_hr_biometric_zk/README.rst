=========================
Biometric Attendance: TCP
=========================

For Odoo 15 Community, by `Odoo Mates <https://github.com/odoomates/hr>`_.

Adds to *Biometric Attendance* the devices Odoo reads over the network, for
the ZKTeco and eSSL devices without ADMS, or on a network the device cannot
leave.

Features
========

* **TCP (Pull)** devices: Odoo connects to the device at its IP address on port
  4370, over TCP, or UDP for the older devices, with the communication key of
  the device. Our own client, on the Python standard library: no external
  library.
* Every 10 minutes, or with *Download Now*, Odoo reads the punches and keeps
  only those not received yet; they are processed like the ADMS punches (modes,
  repeated punches, forgotten check-outs, unknown users).
* *Test Connection* reads the model, serial number and firmware of the device.
* Device users downloaded, employees sent to the device or removed from it,
  clock set, restart: at once, through one connection.
* Fingerprints read from the device to copy a user to other devices, without
  keeping them in Odoo; enrollment of a finger started from Odoo.
* The device is locked only while Odoo writes to it, and always unlocked again;
  it never stops taking punches during a download.
* *Clear Punches on Device* (attendance managers): the punches are downloaded
  first, then deleted from that device only, never from Odoo.
* A device that cannot be reached shows its last error and is *Offline*; the
  other devices go on.

Configuration
=============

#. On the device, Menu > Communication > Ethernet: a fixed IP address; Menu >
   Communication > PC Connection: the communication key (0 when none).
#. Odoo must reach the device on port 4370: on the same network, or through a
   VPN or a port forwarded by the router.
#. Attendances > Biometric > Configuration > Devices: a device with the *TCP
   (Pull)* protocol, its IP address, port and communication key; *Test
   Connection*.

For punches in real time, or a device Odoo cannot reach, use ADMS (in
*Biometric Attendance*).

Dependencies
============

* ``om_hr_biometric`` (Biometric Attendance)

Support
=======

Odoo Mates, odoomates@gmail.com
