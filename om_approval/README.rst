=========
Approvals
=========

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Approval flows for any app, not only HR: put a button of any model under
approval, e.g. Confirm on the sale orders above 10,000, and it waits for its
approvals before it runs. Other modules use the same flows to approve their
own documents, such as the HR requests and the loans.

Features
========

* An approval flow per button of any model, chosen from the buttons of its form
  and list views, without any development.
* A flow applies to the records matching its domain, e.g. the orders above an
  amount, and to one company or all of them. The first matching flow is used.
* Steps approved in turn, by given users, by the users of a group, or by the
  user a field of the record names, e.g. ``user_id`` for the salesperson. A
  step can apply only to some records.
* A step finding nobody is approved by the fallback group of the flow, by
  default the approval administrators.
* The requester may approve his own steps, or leave them to somebody else.
* Clicking the button asks for the approval and tells the user who it waits
  for, with the message of the flow. Once approved, the button runs as the
  requester, or the requester clicks it again.
* Each approver gets an Approval activity; the record and the requester are
  told of the decisions. A refusal asks for a reason.
* Approvals > To Approve lists what waits for you, from every app; My Requests
  follows the approvals you asked for; All Requests shows them all to the
  approval administrators.
* Delegations: an approver away names a substitute for a period, for every
  flow or some of them (Approvals > My Delegations); the approval
  administrators delegate for anyone. The substitute is asked the steps waiting
  for the approver, decides "on behalf of" them, and the approver still can:
  the first decision counts. The substitute of a substitute is followed too;
  the requester never stands in for their own request unless the flow lets
  them approve it.
* A substitute set in the preferences of each user, suggested on their
  delegations.
* Reminders and escalation per step: the approvers are reminded after some
  days, then other users are asked to decide too: given users, a group, or the
  fallback group of the flow.
* For developers: a model inheriting ``approval.mixin`` gets an approval of
  its own, submitted, approved, refused, cancelled or set back to draft.

Configuration
=============

* Give the Administrator access of Approvals to the people who set up the
  flows; they can also approve any step.
* Create the flows in Approvals > Configuration > Approval Flows: the model,
  the button (refresh the list after installing a module), the domain, the
  steps, the fallback group, and the message shown to the requester.

Usage
=====

* Click a button under approval: a notification says the approval is asked.
* The approvers open Approvals > To Approve and approve or refuse.
* Approval rules stop the buttons clicked in the web client and the same
  methods called through the web client's RPC; server code calling the method
  directly is not stopped.

Editions
========

Works with Odoo 20 Community and Odoo 20 Enterprise. On Enterprise, it cannot
be installed together with the Enterprise Approvals app (``approvals``): both define
the same records. Use one or the other.

Dependencies
============

* Base (``base``), Discuss (``mail``) and Web (``web``)

Support
=======

Odoo Mates, odoomates@gmail.com
