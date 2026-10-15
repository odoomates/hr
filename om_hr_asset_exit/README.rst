==================
HR Assets in Exits
==================

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Links HR Assets to HR Exit: a leaving employee is cleared only once the assets
in their hands are back.

Features
========

* When an exit is approved, each asset the employee still holds becomes a line
  of its clearance, e.g. "Return: Laptop/SN123", with a to-do for the
  technician of the asset (or of its category).
* The line is cleared when the asset is returned or reported lost, whoever
  takes it back, and its to-do is marked done.
* The line cannot be cleared by hand, nor marked not needed, while the asset is
  still out, so the exit is closed only once everything is back.
* The asset of each clearance line can be shown in the clearance list of the
  exit (optional column Asset).

Usage
=====

#. Approve the exit of an employee holding assets: the clearance gets a line
   per asset.
#. Take each asset back from its form in Employees > Assets > Assets, with
   Return or Report Lost: its line is cleared.

Dependencies
============

Installs by itself with HR Assets (``om_hr_asset``) and HR Exit
(``om_hr_exit``).

Support
=======

Odoo Mates, odoomates@gmail.com
