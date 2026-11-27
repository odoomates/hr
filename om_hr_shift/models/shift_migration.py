""" The shifts of the former versions move to the planning, on the update of the module: templates, rotations, shifts
(slots on the resource of their employee), shift requests, unavailability (time off of the resource) and the rules of
the companies. The id of each former record is kept on the new one (old_..._id) and their external ids point to the
new records. The former tables are left as they are, without their foreign keys, so that nothing is lost and no
deletion is ever blocked by them. """
import logging
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import api, models
from odoo.fields import Command
from odoo.tools import sql

_logger = logging.getLogger(__name__)

DONE = 'om_hr_shift.planning_migration'
LEGACY_TABLES = ('hr_shift', 'hr_shift_template', 'hr_shift_rotation', 'hr_shift_rotation_line', 'hr_shift_request',
                 'hr_shift_unavailability', 'hr_shift_resource_calendar_attendance_rel',
                 'hr_department_hr_shift_template_rel', 'hr_job_hr_shift_template_rel')
REQUEST_STATES = {'draft': 'draft', 'to_accept': 'to_accept', 'to_approve': 'pending', 'approved': 'approved',
                  'refused': 'refused', 'cancel': 'cancelled'}
NEW_MODELS = {'hr.shift': 'om.planning.slot', 'hr.shift.template': 'om.planning.template',
              'hr.shift.rotation': 'om.planning.rotation', 'hr.shift.request': 'om.planning.request',
              'hr.shift.unavailability': 'resource.calendar.leaves'}
CONTEXT = {'om_hr_shift_migration': True, 'om_hr_shift_no_roster': True, 'om_planning_no_recurrence': True,
           'om_planning_no_follower_sync': True, 'tracking_disable': True, 'mail_create_nolog': True,
           'mail_create_nosubscribe': True, 'mail_notrack': True, 'active_test': False}


def worked_hours(hour_from, hour_to, break_from, break_to):
    """ The hours worked of a former shift and its break, as the former shifts computed them. """
    overnight = hour_to <= hour_from
    end = hour_to + (24 if overnight else 0)
    total = end - hour_from
    if break_to != break_from:
        start_break = break_from + (24 if overnight and break_from < hour_from else 0)
        end_break = break_to + (24 if overnight and break_to <= hour_from else 0)
        if hour_from <= start_break < end_break <= end:
            return total - (end_break - start_break), end_break - start_break
    return total, 0.0


def fetch(cr, query, params=None):
    cr.execute(query, params)
    columns = [column[0] for column in cr.description]
    return [dict(zip(columns, row, strict=True)) for row in cr.fetchall()]


def keep_dates(cr, table, mapping, old_table):
    """ The new records keep who created and changed the former ones, and when. """
    for old_id, new_id in mapping.items():
        cr.execute(f"""
            UPDATE {table} t SET create_uid = o.create_uid, create_date = o.create_date,
                                 write_uid = o.write_uid, write_date = o.write_date
              FROM {old_table} o WHERE o.id = %s AND t.id = %s
        """, (old_id, new_id))  # noqa: S608


def repoint_xmlids(env, model, new_model, mapping):
    """ The external ids of the former records point to the new records. """
    cr = env.cr
    for row in fetch(cr, "SELECT id, res_id FROM ir_model_data WHERE module = 'om_hr_shift' AND model = %s",
                     (model,)):
        new_id = mapping.get(row['res_id'])
        if new_id:
            cr.execute("UPDATE ir_model_data SET model = %s, res_id = %s WHERE id = %s",
                       (new_model, new_id, row['id']))
        else:
            cr.execute("DELETE FROM ir_model_data WHERE id = %s", (row['id'],))


def migrate_templates(env):
    cr = env.cr
    Template = env['om.planning.template'].with_context(CONTEXT)
    departments, jobs = {}, {}
    for row in fetch(cr, "SELECT * FROM hr_department_hr_shift_template_rel"):
        departments.setdefault(row['hr_shift_template_id'], []).append(row['hr_department_id'])
    for row in fetch(cr, "SELECT * FROM hr_job_hr_shift_template_rel"):
        jobs.setdefault(row['hr_shift_template_id'], []).append(row['hr_job_id'])
    mapping = {}
    for old in fetch(cr, "SELECT * FROM hr_shift_template ORDER BY id"):
        _hours, break_hours = worked_hours(old['hour_from'], old['hour_to'], old['break_from'] or 0.0,
                                           old['break_to'] or 0.0)
        values = {
            'code': old['code'], 'sequence': old['sequence'], 'active': old['active'],
            'start_time': old['hour_from'], 'end_time': old['hour_to'],
            'break_hours': break_hours, 'break_from': old['break_from'] if break_hours else 0.0,
            'color': old['color'], 'company_id': old['company_id'],
            'department_ids': [Command.set(departments.get(old['id'], []))],
            'job_ids': [Command.set(jobs.get(old['id'], []))],
            'work_entry_type_id': old['work_entry_type_id'], 'allowance': old['allowance'] or 0.0,
            'currency_id': old['currency_id'], 'old_template_id': old['id'],
        }
        template = Template.create(dict(values, name='/'))
        # the name with its translations
        cr.execute("UPDATE om_planning_template t SET name = o.name FROM hr_shift_template o "
                   "WHERE o.id = %s AND t.id = %s", (old['id'], template.id))
        mapping[old['id']] = template.id
    keep_dates(cr, 'om_planning_template', mapping, 'hr_shift_template')
    repoint_xmlids(env, 'hr.shift.template', 'om.planning.template', mapping)
    env['om.planning.template'].invalidate_model()
    return mapping


def migrate_rotations(env, templates):
    cr = env.cr
    Rotation = env['om.planning.rotation'].with_context(CONTEXT)
    mapping = {}
    for old in fetch(cr, "SELECT * FROM hr_shift_rotation ORDER BY id"):
        lines = fetch(cr, "SELECT * FROM hr_shift_rotation_line WHERE rotation_id = %s ORDER BY sequence, id",
                      (old['id'],))
        values = {
            'active': old['active'], 'company_id': old['company_id'], 'old_rotation_id': old['id'],
            'line_ids': [Command.clear()] + [Command.create({
                'sequence': line['sequence'], 'template_id': templates.get(line['template_id'], False)})
                for line in lines],
        }
        rotation = Rotation.create(dict(values, name='/'))
        cr.execute("UPDATE om_planning_rotation t SET name = o.name FROM hr_shift_rotation o "
                   "WHERE o.id = %s AND t.id = %s", (old['id'], rotation.id))
        mapping[old['id']] = rotation.id
    keep_dates(cr, 'om_planning_rotation', mapping, 'hr_shift_rotation')
    repoint_xmlids(env, 'hr.shift.rotation', 'om.planning.rotation', mapping)
    env['om.planning.rotation'].invalidate_model()
    return mapping


def migrate_shifts(env, templates):
    """ Each shift becomes a slot of the resource of its employee, at the same moments: the start and end the
        former shift had computed from its day and hours in the timezone of the employee. """
    cr = env.cr
    Slot = env['om.planning.slot'].with_context(CONTEXT)
    employees = {employee.id: employee for employee in env['hr.employee'].with_context(active_test=False).search([])}
    mapping = {}
    olds = fetch(cr, "SELECT * FROM hr_shift ORDER BY id")
    for old in olds:
        employee = employees.get(old['employee_id'])
        company_id = old['company_id']
        start, stop = old['start'], old['stop']
        if not (start and stop):
            tz = ZoneInfo((employee and employee.resource_id.tz) or env['res.company'].browse(company_id).partner_id.tz
                          or 'UTC')
            overnight = old['hour_to'] <= old['hour_from']
            start = (datetime.combine(old['date'], time.min) + timedelta(hours=old['hour_from'])).replace(tzinfo=tz)
            stop = (datetime.combine(old['date'] + timedelta(days=1 if overnight else 0), time.min)
                    + timedelta(hours=old['hour_to'])).replace(tzinfo=tz)
            start, stop = (moment.astimezone(UTC).replace(tzinfo=None) for moment in (start, stop))
        _hours, break_hours = worked_hours(old['hour_from'], old['hour_to'], old['break_from'] or 0.0,
                                           old['break_to'] or 0.0)
        resource = employee.resource_id if employee else env['resource.resource']
        if resource.company_id and resource.company_id.id != company_id:
            _logger.info('Shift %s: in the company of the resource of its employee', old['id'])
            company_id = resource.company_id.id
        values = {
            'resource_ids': [Command.set(resource.ids)],
            'company_id': company_id,
            'template_id': templates.get(old['template_id'], False),
            'start_datetime': start,
            'end_datetime': stop,
            'break_hours': break_hours,
            'break_from': old['break_from'] if break_hours else 0.0,
            'state': old['state'],
            'note': old['note'],
            'old_shift_id': old['id'],
        }
        if not employee and old['department_id']:
            values['department_id'] = old['department_id']
        if old['state'] == 'published':
            values['publication_date'] = old['write_date']
        mapping[old['id']] = Slot.create(values).id
    keep_dates(cr, 'om_planning_slot', mapping, 'hr_shift')
    # the day of the shift, as the former shift had it, and its lines of the roster schedule
    cr.execute("""
        UPDATE om_planning_slot s SET shift_date = h.date FROM hr_shift h WHERE s.old_shift_id = h.id
    """)
    cr.execute("""
        INSERT INTO om_planning_slot_roster_attendance_rel (slot_id, attendance_id)
        SELECT s.id, r.resource_calendar_attendance_id
          FROM hr_shift_resource_calendar_attendance_rel r
          JOIN om_planning_slot s ON s.old_shift_id = r.hr_shift_id
          JOIN resource_calendar_attendance a ON a.id = r.resource_calendar_attendance_id
        ON CONFLICT DO NOTHING
    """)
    repoint_xmlids(env, 'hr.shift', 'om.planning.slot', mapping)
    env['om.planning.slot'].invalidate_model()
    return mapping


def migrate_requests(env, slots):
    cr = env.cr
    Request = env['om.planning.request'].with_context(CONTEXT)
    resources = {employee.id: employee.resource_id
                 for employee in env['hr.employee'].with_context(active_test=False).search([])}
    mapping = {}
    for old in fetch(cr, "SELECT * FROM hr_shift_request ORDER BY id"):
        if old['shift_id'] not in slots or old['employee_id'] not in resources:
            continue
        state = REQUEST_STATES.get(old['state'], 'cancelled')
        values = {
            'request_type': 'claim' if old['kind'] == 'claim' else 'switch',
            'slot_id': slots[old['shift_id']],
            'resource_id': resources[old['employee_id']].id,
            'reason': old['note'],
            'state': 'cancelled',
            'old_request_id': old['id'],
        }
        if old['kind'] == 'swap':
            values['target_slot_id'] = slots.get(old['target_shift_id'], False)
            target = resources.get(old['target_employee_id'])
            values['target_resource_id'] = target.id if target else False
        request = Request.create(values)
        # the state as it was, without the checks of a new request
        cr.execute("UPDATE om_planning_request SET state = %s, approval_state = %s, approver_id = %s WHERE id = %s",
                   (state, old['approval_state'] or 'draft',
                    old['write_uid'] if state in ('approved', 'refused') else None, request.id))
        mapping[old['id']] = request.id
    keep_dates(cr, 'om_planning_request', mapping, 'hr_shift_request')
    env['om.planning.request'].invalidate_model()
    # their messages and followers
    for old_id, new_id in mapping.items():
        cr.execute("UPDATE mail_message SET model = 'om.planning.request', res_id = %s "
                   "WHERE model = 'hr.shift.request' AND res_id = %s", (new_id, old_id))
        cr.execute("""
            UPDATE mail_followers f SET res_model = 'om.planning.request', res_id = %s
             WHERE f.res_model = 'hr.shift.request' AND f.res_id = %s AND NOT EXISTS (
                SELECT 1 FROM mail_followers n
                 WHERE n.res_model = 'om.planning.request' AND n.res_id = %s AND n.partner_id = f.partner_id)
        """, (new_id, old_id, new_id))
    # their approvals, those waiting included, go on with the new requests
    if sql.table_exists(cr, 'approval_request'):
        for old_id, new_id in mapping.items():
            cr.execute("UPDATE approval_request SET res_model = 'om.planning.request', res_id = %s "
                       "WHERE res_model = 'hr.shift.request' AND res_id = %s", (new_id, old_id))
        env['approval.request'].invalidate_model()
    repoint_xmlids(env, 'hr.shift.request', 'om.planning.request', mapping)
    return mapping


def migrate_unavailability(env):
    """ The days an employee cannot work become time off of their resource, from the start of the first day to the
        end of the last one in their timezone. """
    cr = env.cr
    Leave = env['resource.calendar.leaves'].with_context(CONTEXT)
    employees = {employee.id: employee for employee in env['hr.employee'].with_context(active_test=False).search([])}
    mapping = {}
    for old in fetch(cr, "SELECT * FROM hr_shift_unavailability ORDER BY id"):
        employee = employees.get(old['employee_id'])
        if not employee:
            continue
        tz = ZoneInfo(employee.resource_id.tz or employee.company_id.partner_id.tz or 'UTC')
        start = datetime.combine(old['date_from'], time.min, tzinfo=tz)
        stop = datetime.combine(old['date_to'], time.max.replace(microsecond=0), tzinfo=tz)
        mapping[old['id']] = Leave.create({
            'name': old['reason'] or env._('Unavailable'),
            'resource_id': employee.resource_id.id,
            'calendar_id': employee.resource_id.calendar_id.id,
            'company_id': employee.company_id.id,
            'date_from': start.astimezone(UTC).replace(tzinfo=None),
            'date_to': stop.astimezone(UTC).replace(tzinfo=None),
            'shift_unavailability': True,
            'old_unavailability_id': old['id'],
        }).id
    keep_dates(cr, 'resource_calendar_leaves', mapping, 'hr_shift_unavailability')
    repoint_xmlids(env, 'hr.shift.unavailability', 'resource.calendar.leaves', mapping)
    return mapping


def migrate_settings(env):
    """ The rules of the roster become the planning rules of the companies. """
    cr = env.cr
    if not sql.column_exists(cr, 'res_company', 'shift_min_rest'):
        return
    cr.execute("""
        UPDATE res_company SET planning_min_rest_hours = COALESCE(shift_min_rest, 0),
                               planning_max_hours_week = COALESCE(shift_max_week_hours, 0)
    """)
    env['res.company'].invalidate_model(['planning_min_rest_hours', 'planning_max_hours_week'])


def migrate_groups(env):
    """ The shift planners plan with the planning engine. """
    planner = env.ref('om_hr_shift.group_shift_planner', raise_if_not_found=False)
    manager = env.ref('om_planning.group_planning_manager', raise_if_not_found=False)
    if planner and manager and manager not in planner.implied_ids:
        planner.write({'implied_ids': [Command.link(manager.id)]})


def migrate_approvals(env):
    """ The approval flows of the former models apply to the new ones, their approval requests to the new
        records: the shift requests waiting for an approval wait for it still. """
    cr = env.cr
    if not sql.table_exists(cr, 'approval_rule'):
        return
    for old, new in NEW_MODELS.items():
        cr.execute("SELECT id FROM ir_model WHERE model = %s", (old,))
        old_row = cr.fetchone()
        new_model = env['ir.model']._get(new)
        if not old_row or not new_model:
            continue
        params = {'old': old_row[0], 'new': new_model.id, 'model': new}
        cr.execute("""
            UPDATE approval_button b SET model_id = %(new)s, model = %(model)s
             WHERE b.model_id = %(old)s AND NOT EXISTS (
                SELECT 1 FROM approval_button n WHERE n.model_id = %(new)s AND n.method = b.method)
        """, params)
        # a button the new model has already: the flows take it
        cr.execute("""
            UPDATE approval_rule r SET button_id = n.id
              FROM approval_button b, approval_button n
             WHERE r.button_id = b.id AND b.model_id = %(old)s AND n.model_id = %(new)s AND n.method = b.method
        """, params)
        cr.execute("UPDATE approval_rule SET model_id = %(new)s, model = %(model)s WHERE model_id = %(old)s",
                   params)
    env['approval.rule'].invalidate_model()
    env['approval.button'].invalidate_model()


def release_legacy_tables(cr):
    """ The former tables stay, without the foreign keys that could block the deletion of a record. """
    for table in LEGACY_TABLES:
        if not sql.table_exists(cr, table):
            continue
        cr.execute("""
            SELECT conname FROM pg_constraint WHERE contype = 'f' AND conrelid = %s::regclass
        """, (table,))
        for (name,) in cr.fetchall():
            cr.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{name}"')


class OmPlanningSlot(models.Model):
    _inherit = 'om.planning.slot'

    @api.model
    def _shift_migrate_legacy(self):
        """ Run on each update of the module, before its data: once, when the tables of the former shifts are
            there. """
        cr = self.env.cr
        env = self.sudo().env
        if not sql.table_exists(cr, 'hr_shift') or env['ir.config_parameter'].get_bool(DONE):
            return
        templates = migrate_templates(env)
        rotations = migrate_rotations(env, templates)
        slots = migrate_shifts(env, templates)
        requests = migrate_requests(env, slots)
        unavailability = migrate_unavailability(env)
        migrate_settings(env)
        migrate_groups(env)
        migrate_approvals(env)
        release_legacy_tables(cr)
        env['ir.config_parameter'].set_bool(DONE, True)
        _logger.info('Shifts moved to the planning: %s templates, %s rotations, %s shifts, %s requests, '
                     '%s unavailability', len(templates), len(rotations), len(slots), len(requests),
                     len(unavailability))
