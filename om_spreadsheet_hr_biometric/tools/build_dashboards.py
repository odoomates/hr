#!/usr/bin/env python3
""" Write the Biometric Attendance dashboard of om_spreadsheet_hr_biometric into data/files.

    python3 om_spreadsheet_hr_biometric/tools/build_dashboards.py

It reads the punches of the biometric devices and the attendances they made. Everything follows the Period and
Device filters. The builder is in om_spreadsheet_hr/tools, used at build time only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'om_spreadsheet_hr', 'tools'))

from spreadsheet_builder import (  # noqa: E402
    GREEN, HEADER, INTEGER_FORMAT, RED, TEXT, Workbook, cards, dashboard_sheet, label,
)

FILES = os.path.join(os.path.dirname(HERE), 'data', 'files')

CARD_WIDTH = 240
GAP = 10
FULL_WIDTH = 4 * CARD_WIDTH + 3 * GAP
HALF_WIDTH = (FULL_WIDTH - GAP) // 2

PUNCHES = []
UNMAPPED = [['state', '=', 'unmapped']]
ERRORS = [['state', '=', 'error']]
REVIEW = [['biometric_review', '=', True]]
DONE = [['state', '=', 'done']]
LOG_ACTION = 'om_hr_biometric.hr_biometric_log_action'


def build_biometric():
    workbook = Workbook('hr_biometric')
    dashboard = dashboard_sheet(workbook)
    data = workbook.sheet('Data')
    period = workbook.date_filter('period', 'Period', 'this_month')
    device = workbook.relation_filter('device', 'Device', 'hr.biometric.device')
    log_matching = {period: ('timestamp', 'datetime'), device: ('device_id', 'many2one')}
    attendance_matching = {period: ('check_in', 'datetime'), device: ('in_device_id', 'many2one')}

    punches = workbook.pivot('Punches', 'hr.biometric.log', PUNCHES, ['__count'], field_matching=log_matching)
    unmapped = workbook.pivot('Unknown Users', 'hr.biometric.log', UNMAPPED, ['__count'], field_matching=log_matching)
    errors = workbook.pivot('Punch Errors', 'hr.biometric.log', ERRORS, ['__count'], field_matching=log_matching)
    review = workbook.pivot('To Review', 'hr.attendance', REVIEW, ['__count'], field_matching=attendance_matching)
    rows = [
        ('Punches', '=0+PIVOT.VALUE(%s,"__count")' % punches),
        ('Punches of unknown users', '=0+PIVOT.VALUE(%s,"__count")' % unmapped),
        ('Punches in error', '=0+PIVOT.VALUE(%s,"__count")' % errors),
        ('Attendances to review', '=0+PIVOT.VALUE(%s,"__count")' % review),
    ]
    for row, (text, formula) in enumerate(rows):
        data.set(0, row, label(text), TEXT)
        data.set(1, row, formula, fmt=INTEGER_FORMAT)
    data.col_sizes.update({0: 220, 1: 120})

    cards(dashboard, [
        ('punches', 'Punches', 'Data!B1', None, None, GREEN, RED),
        ('unmapped', 'Unknown Users', 'Data!B2', None, None, RED, GREEN),
        ('errors', 'Punch Errors', 'Data!B3', None, None, RED, GREEN),
        ('review', 'Attendances to Review', 'Data!B4', None, None, RED, GREEN),
    ], CARD_WIDTH, per_row=4)

    charts = [
        ('daily', 'bar', 'Punches by Day', 'hr.biometric.log', '__count', 'timestamp:day', PUNCHES, log_matching,
         LOG_ACTION),
        ('device', 'pie', 'Punches by Device', 'hr.biometric.log', '__count', 'device_id', PUNCHES, log_matching,
         LOG_ACTION),
        ('verify', 'pie', 'Punches by Verification', 'hr.biometric.log', '__count', 'verify_type', DONE,
         log_matching, LOG_ACTION),
        ('state', 'bar', 'Punches by Status', 'hr.biometric.log', '__count', 'state', PUNCHES, log_matching,
         LOG_ACTION),
    ]
    for index, (key, chart_type, title, model, measure, group_by, domain, matching, action) in enumerate(charts):
        x = (index % 2) * (HALF_WIDTH + GAP)
        y = 130 + (index // 2) * 290
        dashboard.odoo_chart(key, chart_type, title, model, measure, [group_by], domain, x, y, HALF_WIDTH, 280,
                             field_matching=matching, action_xmlid=action)

    devices = workbook.odoo_list(
        'Devices', 'hr.biometric.device', [],
        [('name', 'Device'), ('protocol', 'Protocol'), ('last_contact', 'Last Contact'),
         ('device_log_count', 'Punches on Device'), ('firmware_version', 'Firmware')],
        order_by=[('last_contact', False)])
    title_row = 32
    dashboard.set(0, title_row, label('Devices'), HEADER)
    dashboard.set(0, title_row + 1, '=ODOO.LIST(%s,20)' % devices)
    workbook.dump(os.path.join(FILES, 'biometric_dashboard.json'))


if __name__ == '__main__':
    build_biometric()
    print('Wrote', os.path.join(FILES, 'biometric_dashboard.json'))
