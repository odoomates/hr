====
Sign
====

Part of `Odoo Mates HR <https://github.com/odoomates/hr>`_, the HR suite of Odoo Mates for Odoo 20
Community.

Send prints and PDF files for electronic signature. The signers sign from a
link sent by email, without an account, in the order set, and everyone gets
the signed PDF with a signature certificate.

Features
========

* Send an issued print for signature, or upload any PDF, e.g. a contract
  written by a lawyer.
* The print templates name who signs: a contact or user of a field of the
  record, a given contact, or the person sending. The signers of the same
  sequence sign together; the next ones are asked once they signed.
* Placeholders such as ``[signature: Employee]`` put a signature where it
  belongs in the text; the others sign below it. An uploaded PDF gets a
  signature page at the end.
* The signers draw, type or upload their signature on a phone or a computer,
  or decline with a reason.
* Optionally, a code sent by email that the signer enters before signing.
* Reminders every few days, and a deadline after which the request expires.
* The signed PDF ends with a certificate: who signed, when, from which IP
  address and browser, and the SHA-256 fingerprint of the document sent. A
  public page confirms a signed document from its reference.
* Everything that happens is kept as evidence that nobody can change.
* The signers find the documents sent to them in the Signatures page of the
  portal; users of the backend sign from Sign > To Sign.
* Developers: a mixin gives any model a Signatures smart button and hooks
  called when a document about the record is signed, declined or cancelled.

Configuration
=============

* Give the User access of Sign to the people who send documents for signature,
  and the Administrator access to the people who see all the requests.
* On a print template, the Signers tab lists who signs, whether an email code
  is needed, the days to sign and the days between reminders.

Usage
=====

* On an issued print, Send for Signature opens the request with its signers:
  check them, add a message, and Send. Issue & Send for Signature from the
  Print menu does both at once.
* Sign > Requests > New uploads a PDF to send.
* The signed PDF is attached to the request and sent to everyone.

Dependencies
============

* Print Templates (``om_print_template``)
* Portal (``portal``)

Support
=======

Odoo Mates, odoomates@gmail.com
