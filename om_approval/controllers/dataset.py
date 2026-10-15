# The approval rules stop the buttons clicked in the web client, which call call_button, and the same methods
# called by hand through call_kw. Server code calling a method directly is never stopped.
from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.dataset import DataSet

from ..models.om_approval_button import NOT_BUTTONS


def _record_ids(args):
    ids = args[0] if args else None
    if isinstance(ids, int) and not isinstance(ids, bool):
        return [ids]
    if isinstance(ids, (list, tuple)) and all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
        return list(ids)
    return None


def _gate(model, method, args):
    """ :return: the action replacing the call when the button waits for an approval, else None """
    if method in NOT_BUTTONS or method.startswith('_') or model not in request.env:
        return None
    if not request.env['om.approval.flow']._has_button_flows(model, method):
        return None
    ids = _record_ids(args)
    if not ids:
        return None
    return request.env['om.approval.request']._gate_button(model, method, ids)


class DataSetApproval(DataSet):

    @http.route()
    def call_kw(self, model, method, args, kwargs, path=None):
        action = _gate(model, method, args)
        if action is not None:
            return action
        return super().call_kw(model, method, args, kwargs, path=path)

    @http.route()
    def call_button(self, model, method, args, kwargs, path=None):
        action = _gate(model, method, args)
        if action is not None:
            return action
        return super().call_button(model, method, args, kwargs, path=path)
