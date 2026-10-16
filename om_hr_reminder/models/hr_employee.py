from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


def next_yearly(day, today, after=None):
    """ :return: the next date, from today on, falling on the day and the month of `day`; the 29th of February is
        kept on the 28th in the other years. `after`: the year must come after it, e.g. an anniversary. """
    def in_year(year):
        try:
            return day.replace(year=year)
        except ValueError:
            return date(year, 2, 28)
    year = today.year if after is None else max(today.year, after.year + 1)
    candidate = in_year(year)
    if candidate < today:
        candidate = in_year(year + 1)
    return candidate


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # stored, so that the Automation Rules can remind on them; kept up to date by a daily job
    next_birthday = fields.Date(string='Next Birthday', readonly=True, copy=False, index=True,
                                   help='Only for the employees who let their birthday be shown.')
    next_anniversary = fields.Date(string='Next Work Anniversary', readonly=True, copy=False, index=True)
    service_years = fields.Integer(string='Years of Service at the Anniversary', readonly=True, copy=False)
    probation_end = fields.Date(string='Probation Ends', readonly=True, copy=False, groups='hr.group_hr_user')

    def _reminder_dates(self, today):
        self.ensure_one()
        employee = self.sudo()
        start = employee.version_id.contract_date_start
        anniversary = next_yearly(start, today, after=start) if start else False
        return {
            # only for the employees who let their birthday be shown, as core Odoo asks
            'next_birthday': next_yearly(employee.birthday, today)
            if employee.birthday and employee.birthday_public_display else False,
            'next_anniversary': anniversary,
            'service_years': anniversary.year - start.year if anniversary else 0,
            'probation_end': employee.version_id.trial_date_end or False,
        }

    def _update_reminder_dates(self, today=None):
        today = today or fields.Date.context_today(self)
        for employee in self.sudo():
            values = employee._reminder_dates(today)
            changed = {name: value for name, value in values.items() if employee[name] != value}
            if changed:
                super(HrEmployee, employee.with_context(tracking_disable=True)).write(changed)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._update_reminder_dates()
        return employees

    def write(self, vals):
        result = super().write(vals)
        if {'birthday', 'birthday_public_display', 'version_id', 'contract_date_start', 'trial_date_end'} & set(vals):
            self._update_reminder_dates()
        return result

    @api.model
    def _cron_update_reminder_dates(self):
        self.search([])._update_reminder_dates()

    # ------------------------------------------------------------------
    # Reminders, called by the Automation Rules
    # ------------------------------------------------------------------

    def _reminder_users(self, with_hr=False):
        """ :return: who is reminded about the employee: the manager, with the HR responsible if asked; the HR
            managers when nobody else """
        self.ensure_one()
        employee = self.sudo()
        users = employee.parent_id.user_id
        if with_hr or not users:
            users |= employee.version_id.hr_responsible_id
        if not users:
            users = self.env.ref('hr.group_hr_manager').sudo().all_user_ids.filtered(
                lambda user: employee.company_id in user.company_ids)
        return users.filtered(lambda user: user.active and not user.share)

    def _remind(self, kind):
        """ A to-do for the people the employee's kind of reminder is for. """
        for employee in self.sudo():
            if kind == 'birthday':
                summary = _('Birthday of %s', employee.name)
                deadline, users = employee.next_birthday, employee._reminder_users()
            elif kind == 'anniversary':
                summary = _('%(years)s years of service of %(employee)s', years=employee.service_years,
                            employee=employee.name)
                deadline, users = employee.next_anniversary, employee._reminder_users(with_hr=True)
            elif kind == 'probation':
                if 'hr.appraisal' in self.env:
                    # HR Appraisals already creates the probation review for the manager
                    continue
                summary = _('The probation of %s ends', employee.name)
                deadline, users = employee.probation_end, employee._reminder_users()
            else:
                raise ValueError(kind)
            for user in users:
                employee.activity_schedule('mail.mail_activity_data_todo', date_deadline=deadline, summary=summary,
                                           user_id=user.id)


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # the celebrations the employees see: read from the employee table by the public view
    next_birthday = fields.Date(string='Next Birthday', readonly=True)
    next_anniversary = fields.Date(string='Next Work Anniversary', readonly=True)
    service_years = fields.Integer(string='Years of Service at the Anniversary', readonly=True)
