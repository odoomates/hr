============
HR Approvals
============

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Brings the employees into the approval flows of Approvals (``om_approval``):
the manager, the department manager, the coach or the HR responsible approve,
for the HR documents and for the buttons of any app. Employees also send HR
requests, approved along a flow.

Features
========

* New approvers for the steps of any flow: Manager of the Employee, Manager of
  the Department, Coach of the Employee and HR Responsible of the Contract.
  The employee is the one the record is about, else the employee of the
  requester, e.g. the salesperson confirming a sale order.
* A step by field can also point to an employee, e.g. ``employee_id.parent_id``.
* In a flow where the requester does not approve his own steps, the employee
  the request is for does not approve it either, e.g. when HR asks on his
  behalf, unless nobody else can.
* HR requests: employees ask HR for a document, a change of their details or
  anything else, in My HR > My Requests. The request goes to their manager,
  then to the HR officers.
* Request categories with a description shown to the employee: Document,
  Change of My Details and Other to start with.
* Employees > Requests > To Approve and All Requests; My HR > To Approve lists
  everything waiting for your approval, from every app.
* A step waiting too long is escalated to the managers of its approvers, by
  default.
* With Time Off, validated time off names the substitute of the approver for
  its dates (HR Approvals: Time Off).

Configuration
=============

* HR managers set who approves the HR documents in Employees > Configuration >
  Requests > Approval Flows, and the categories in Request Categories.

Usage
=====

* The employee creates a request in My HR > My Requests, chooses its category,
  writes the details and submits it.
* The approvers approve or refuse it from Employees > Requests > To Approve or
  My HR > To Approve.

Dependencies
============

* Installs by itself with Approvals (``om_approval``) and HR Base
  (``om_hr_base``).

Support
=======

Odoo Mates, odoomates@gmail.com
