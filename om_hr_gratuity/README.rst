===========
HR Gratuity
===========

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

The end of service gratuity of the employees leaving, computed on their exit
from a scheme the company describes: the days of pay a year of service
earns, by band of years, and the part kept by reason of leaving.

Features
========

* Gratuity schemes: the days of pay per year of service in each band of
  years, e.g. 21 days for each of the first five years and 30 days for each
  year after; the part kept by reason of leaving and years of service, e.g. a
  third for a resignation between 2 and 5 years; a minimum service below
  which no gratuity is due; and a cap in months of wage.
* The Gratuity tab of an exit (HR officers): the scheme, by default the first
  one of the company, and the date the service started, by default the first
  contract date of the employee.
* Compute Gratuity: the years of service up to the last working day, the
  monthly wage of the contract on that day, the days of pay earned, the
  gratuity, and how it was reached, e.g. "5.00 years × 21 days, 3.50 years ×
  30 days".
* The days of pay are paid at the monthly wage over the Days in a Month of
  Pay of the scheme. The part kept is that of the first line matching the
  reason and the years of service; the other reasons keep all of it.
* Registering the departure computes the gratuity when it was not computed
  yet.
* With HR Exit in Payroll, the final settlement payslip pays the gratuity.

Configuration
=============

* Employees > Configuration > Requests > Gratuity Schemes (HR
  administrators): the name, Days in a Month of Pay (e.g. 30, or 26 working
  days), Minimum Service (Years), Cap (Months of Wage), the bands of Days of
  Pay per Year of Service (from, to, days; a band with no end covers every
  year beyond), the lines of Part Kept by Reason of Leaving (reasons, from,
  to, part kept in %), the company and notes. 0 means no minimum or no cap.
  No scheme comes with the module.

Usage
=====

#. Describe the gratuity of the company in a scheme.
#. On an approved exit, open the Gratuity tab, check the scheme and the start
   of service, and click Compute Gratuity.
#. Register the departure; with HR Exit in Payroll, create the final
   settlement.

Dependencies
============

* HR Exit (``om_hr_exit``)

Support
=======

Odoo Mates, odoomates@gmail.com
