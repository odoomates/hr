#!/usr/bin/env python3
""" Write the Time Off and Attendance dashboard of om_spreadsheet_hr_time into data/files.

    python3 om_spreadsheet_hr_time/tools/build_dashboards.py

It reads the time off of the Time Off app and the attendances of the Attendances app: the validated time off by its
first day, the validated attendances by their check in, the overtime being the attendances the time rules create.
Everything follows the Period and Department filters.
The builder is in om_spreadsheet_hr/tools, used at build time only: the module does not need Accounting.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'om_spreadsheet_hr', 'tools'))

from spreadsheet_builder import (  # noqa: E402
    GREEN, HEADER, INTEGER_FORMAT, RED, TEXT, Workbook, cards, dashboard_sheet, label,
)

FILES = os.path.join(os.path.dirname(HERE), 'data', 'files')

DATE_FORMAT = 'mm/dd/yyyy'
MONTH_FORMAT = 'mmm yyyy'
NUMBER_FORMAT = '#,##0.0'
CARD_WIDTH = 240
GAP = 10
FULL_WIDTH = 4 * CARD_WIDTH + 3 * GAP
HALF_WIDTH = (FULL_WIDTH - GAP) // 2

VALIDATED_LEAVES = [['state', '=', 'validate']]
PENDING_LEAVES = [['state', 'in', ['confirm', 'validate1']]]
WORKED = [['state', '=', 'validated'], ['time_rule_id', '=', False]]
OVERTIME = [['state', '=', 'validated'], ['time_rule_id', '!=', False]]


def build_time():
    workbook = Workbook('hr_time')
    dashboard = dashboard_sheet(workbook)
    data = workbook.sheet('Data')
    period = workbook.date_filter('period', 'Period', 'this_year')
    department = workbook.relation_filter('department', 'Department', 'hr.department')
    leave_matching = {period: ('request_date_from', 'date'), department: ('department_id', 'many2one')}
    attendance_matching = {period: ('check_in', 'datetime'), department: ('om_department_id', 'many2one')}

    leaves = workbook.pivot('Time Off', 'hr.leave', VALIDATED_LEAVES, ['number_of_days'],
                            rows=[('request_date_from', 'month')], field_matching=leave_matching)
    pending = workbook.pivot('Pending Requests', 'hr.leave', PENDING_LEAVES, ['__count'],
                             field_matching=leave_matching)
    worked = workbook.pivot('Hours Worked', 'hr.attendance', WORKED, ['worked_hours'],
                            rows=[('check_in', 'month')], field_matching=attendance_matching)
    overtime = workbook.pivot('Overtime Hours', 'hr.attendance', OVERTIME, ['worked_hours'],
                              rows=[('check_in', 'month')], field_matching=attendance_matching)

    rows = [
        ('Period', '=ODOO.FILTER.VALUE("Period")', DATE_FORMAT),
        ('Start', '=IF(ISNUMBER(B1),B1,DATE(YEAR(TODAY()),1,1))', DATE_FORMAT),
        ('Time off (days)', '=0+PIVOT.VALUE(%s,"number_of_days")' % leaves, NUMBER_FORMAT),
        ('Pending requests', '=0+PIVOT.VALUE(%s,"__count")' % pending, INTEGER_FORMAT),
        ('Hours worked', '=0+PIVOT.VALUE(%s,"worked_hours")' % worked, NUMBER_FORMAT),
        ('Overtime hours', '=0+PIVOT.VALUE(%s,"worked_hours")' % overtime, NUMBER_FORMAT),
    ]
    for row, (text, formula, fmt) in enumerate(rows):
        data.set(0, row, label(text), TEXT)
        data.set(1, row, formula, fmt=fmt)
    data.set(2, 0, None, fmt=DATE_FORMAT)

    first = 10
    for col, text in enumerate(['Month', 'Time off (days)', 'Hours worked', 'Overtime hours']):
        data.set(col, first - 1, label(text), HEADER)
    for index in range(12):
        row, line = first + index, first + index + 1
        data.set(0, row, '=EDATE(DATE(YEAR($B$2),MONTH($B$2),1),%s)' % index, fmt=MONTH_FORMAT)
        key = 'TEXT(A%s,"mm/yyyy")' % line
        data.set(1, row, '=0+PIVOT.VALUE(%s,"number_of_days","request_date_from:month",%s)' % (leaves, key),
                 fmt=NUMBER_FORMAT)
        data.set(2, row, '=0+PIVOT.VALUE(%s,"worked_hours","check_in:month",%s)' % (worked, key), fmt=NUMBER_FORMAT)
        data.set(3, row, '=0+PIVOT.VALUE(%s,"worked_hours","check_in:month",%s)' % (overtime, key), fmt=NUMBER_FORMAT)
    last = first + 11
    data.col_sizes.update({0: 200, 1: 130, 2: 130, 3: 130})

    cards(dashboard, [
        ('leaves', 'Time Off (Days)', 'Data!B3', None, None, RED, GREEN),
        ('pending', 'Requests to Approve', 'Data!B4', None, None, RED, GREEN),
        ('worked', 'Hours Worked', 'Data!B5', None, None, GREEN, RED),
        ('overtime', 'Overtime Hours', 'Data!B6', None, None, RED, GREEN),
    ], CARD_WIDTH, per_row=4)

    dashboard.chart('leaves_monthly', 'bar', 'Time Off by Month (Days)', data.range(0, first, 0, last),
                    [(data.range(1, first, 1, last), 'Time Off', None)], 0, 120, HALF_WIDTH, 300)
    dashboard.chart('hours_monthly', 'bar', 'Hours Worked and Overtime by Month', data.range(0, first, 0, last),
                    [(data.range(2, first, 2, last), 'Worked', None),
                     (data.range(3, first, 3, last), 'Overtime', None)],
                    HALF_WIDTH + GAP, 120, HALF_WIDTH, 300, stacked=True)

    charts = [
        ('type', 'pie', 'Time Off by Type (Days)', 'hr.leave', 'number_of_days', 'work_entry_type_id',
         VALIDATED_LEAVES, leave_matching, 'hr_holidays.hr_leave_action_action_approve_department'),
        ('leave_department', 'bar', 'Time Off by Department (Days)', 'hr.leave', 'number_of_days', 'department_id',
         VALIDATED_LEAVES, leave_matching, 'hr_holidays.hr_leave_action_action_approve_department'),
        ('overtime_department', 'bar', 'Overtime by Department (Hours)', 'hr.attendance', 'worked_hours',
         'om_department_id', OVERTIME, attendance_matching, 'hr_attendance.hr_attendance_action'),
        ('worked_department', 'bar', 'Hours Worked by Department', 'hr.attendance', 'worked_hours', 'om_department_id',
         WORKED, attendance_matching, 'hr_attendance.hr_attendance_action'),
    ]
    for index, (key, chart_type, title, model, measure, group_by, domain, matching, action) in enumerate(charts):
        x = (index % 2) * (HALF_WIDTH + GAP)
        y = 430 + (index // 2) * 290
        dashboard.odoo_chart(key, chart_type, title, model, measure, [group_by], domain, x, y, HALF_WIDTH, 280,
                             field_matching=matching, action_xmlid=action)

    requests = workbook.odoo_list(
        'Requests to Approve', 'hr.leave', PENDING_LEAVES,
        [('employee_id', 'Employee'), ('work_entry_type_id', 'Type'), ('request_date_from', 'From'),
         ('request_date_to', 'To'), ('number_of_days', 'Days')],
        order_by=[('request_date_from', True)], field_matching=leave_matching)
    title_row = 46
    dashboard.set(0, title_row, label('Time Off Requests to Approve'), HEADER)
    dashboard.set(0, title_row + 1, '=ODOO.LIST(%s,20)' % requests)
    workbook.dump(os.path.join(FILES, 'time_dashboard.json'))


if __name__ == '__main__':
    build_time()
    print('Wrote', os.path.join(FILES, 'time_dashboard.json'))
