from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError

from odoo.addons.spreadsheet.utils.helpers import spreadsheet_safe_batch


class HrVersion(models.Model):
    _inherit = 'hr.version'

    @api.model
    def _spreadsheet_versions(self, date_from, date_to, departments):
        """ :return: the versions of the employees of the selected companies under contract at some point
            between the two dates, archived ones included: the employees who left still count in the past """
        domain = [
            ('company_id', 'in', self.env.companies.ids),
            ('contract_date_start', '!=', False),
            ('contract_date_start', '<=', date_to),
            '|', ('contract_date_end', '=', False), ('contract_date_end', '>=', date_from),
        ]
        versions = self.sudo().with_context(active_test=False).search(domain)
        if departments:
            names = {name.strip().lower() for name in departments.split(',') if name.strip()}
            versions = versions.filtered(lambda v: (v.department_id.name or '').lower() in names)
        return versions

    @api.model
    def _headcount_versions(self, date, departments):
        """ :return: per employee under contract on the date, the version in effect on that day """
        current = {}
        for version in self._spreadsheet_versions(date, date, departments):
            if version.date_version and version.date_version > date:
                continue
            known = current.get(version.employee_id)
            if not known or (version.date_version or date) > (known.date_version or date):
                current[version.employee_id] = version
        return current

    @api.readonly
    @api.model
    @spreadsheet_safe_batch
    def spreadsheet_fetch_hr(self, args_list):
        """ The figures of the OM.HR spreadsheet formulas, for the companies selected by the user::

            [{measure: 'headcount' | 'joiners' | 'leavers' | 'tenure', date_from: str, date_to: str,
              departments: str (names separated by commas, empty for all)}]

        headcount and tenure are read on date_to; joiners and leavers between the two dates.
        """
        if not self.env.user.has_group('hr.group_hr_user'):
            raise AccessError(self.env._('The HR figures are for the HR officers.'))
        results = []
        for args in args_list:
            measure = args.get('measure')
            date_to = fields.Date.to_date(args.get('date_to')) or fields.Date.context_today(self)
            date_from = fields.Date.to_date(args.get('date_from')) or date_to
            departments = args.get('departments') or ''
            if measure in ('headcount', 'tenure'):
                current = self._headcount_versions(date_to, departments)
                if measure == 'headcount':
                    value = len(current)
                else:
                    starts = self._first_starts(list(current))
                    years = [(date_to - starts[employee]).days / 365.25 for employee in current if starts.get(employee)]
                    value = sum(years) / len(years) if years else 0.0
            elif measure in ('joiners', 'leavers'):
                field = 'contract_date_start' if measure == 'joiners' else 'contract_date_end'
                versions = self._spreadsheet_versions(date_from, date_to, departments).filtered(
                    lambda v: v[field] and date_from <= v[field] <= date_to)
                value = len(versions.employee_id)
            else:
                raise ValueError('Unknown measure %s' % measure)
            results.append({'value': value})
        return results

    @api.model
    def _first_starts(self, employees):
        """ :return: per employee, the first day of their first contract """
        starts = defaultdict(lambda: False)
        if not employees:
            return starts
        versions = self.sudo().with_context(active_test=False).search(
            [('employee_id', 'in', [employee.id for employee in employees]), ('contract_date_start', '!=', False)])
        for version in versions:
            start = starts[version.employee_id]
            if not start or version.contract_date_start < start:
                starts[version.employee_id] = version.contract_date_start
        return starts
