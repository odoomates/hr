#!/usr/bin/env python3
""" Write the Talent and Compliance dashboard of om_spreadsheet_hr_talent into data/files.

    python3 om_spreadsheet_hr_talent/tools/build_dashboards.py

It reads the appraisals, the documents of the employees, the exits and the assets of the Odoo Mates HR apps.
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

CARD_WIDTH = 323
GAP = 10
FULL_WIDTH = 3 * CARD_WIDTH + 2 * GAP
HALF_WIDTH = (FULL_WIDTH - GAP) // 2

OPEN_APPRAISALS = [['state', 'in', ['new', 'self', 'review']]]
DONE_APPRAISALS = [['state', '=', 'done']]
EMPLOYEE_DOCUMENTS = [['res_model', '=', 'hr.employee']]
TO_RENEW = EMPLOYEE_DOCUMENTS + [['state', 'in', ['expiring', 'expired']]]
OPEN_EXITS = [['state', 'in', ['to_approve', 'approved']]]
ASSIGNED_ASSETS = [['asset_state', '=', 'assigned']]


def build_talent():
    workbook = Workbook('hr_talent')
    dashboard = dashboard_sheet(workbook)
    data = workbook.sheet('Data')
    period = workbook.date_filter('period', 'Period', 'this_year')
    department = workbook.relation_filter('department', 'Department', 'hr.department')
    by_department = {department: ('department_id', 'many2one')}

    pivots = {
        'open_appraisals': workbook.pivot('Appraisals to Do', 'hr.appraisal', OPEN_APPRAISALS, ['__count'],
                                          field_matching=by_department),
        'done_appraisals': workbook.pivot('Appraisals Done', 'hr.appraisal', DONE_APPRAISALS, ['__count'],
                                          field_matching={period: ('date_done', 'date'), **by_department}),
        'expiring': workbook.pivot('Documents Expiring', 'document.document',
                                   EMPLOYEE_DOCUMENTS + [['state', 'in', ['expiring']]], ['__count'],
                                   field_matching=by_department),
        'expired': workbook.pivot('Documents Expired', 'document.document',
                                  EMPLOYEE_DOCUMENTS + [['state', 'in', ['expired']]], ['__count'],
                                  field_matching=by_department),
        'exits': workbook.pivot('Exits in Progress', 'hr.exit', OPEN_EXITS, ['__count'],
                                field_matching=by_department),
        'assets': workbook.pivot('Assets Assigned', 'maintenance.equipment', ASSIGNED_ASSETS, ['__count']),
    }
    rows = [
        ('Appraisals to do', 'open_appraisals'),
        ('Appraisals done', 'done_appraisals'),
        ('Documents expiring', 'expiring'),
        ('Documents expired', 'expired'),
        ('Exits in progress', 'exits'),
        ('Assets assigned', 'assets'),
    ]
    for row, (text, key) in enumerate(rows):
        data.set(0, row, label(text), TEXT)
        data.set(1, row, '=0+PIVOT.VALUE(%s,"__count")' % pivots[key], fmt=INTEGER_FORMAT)
    data.col_sizes.update({0: 200, 1: 130})

    cards(dashboard, [
        ('open_appraisals', 'Appraisals to Do', 'Data!B1', None, None, RED, GREEN),
        ('done_appraisals', 'Appraisals Done', 'Data!B2', None, None, GREEN, RED),
        ('expiring', 'Documents Expiring', 'Data!B3', None, None, RED, GREEN),
        ('expired', 'Documents Expired', 'Data!B4', None, None, RED, GREEN),
        ('exits', 'Exits in Progress', 'Data!B5', None, None, RED, GREEN),
        ('assets', 'Assets with Employees', 'Data!B6', None, None, GREEN, RED),
    ], CARD_WIDTH, per_row=3)

    charts = [
        ('ratings', 'bar', 'Ratings of the Appraisals Done', 'hr.appraisal', DONE_APPRAISALS, 'rating_id',
         {period: ('date_done', 'date'), **by_department}, 'om_hr_appraisal.om_hr_appraisal_action'),
        ('appraisal_status', 'pie', 'Appraisals by Status', 'hr.appraisal', [['state', '!=', 'cancel']], 'state',
         by_department, 'om_hr_appraisal.om_hr_appraisal_action'),
        ('exit_reasons', 'bar', 'Exits by Reason', 'hr.exit', [['state', 'in', ['approved', 'done']]],
         'departure_reason_id', {period: ('date_notice', 'date'), **by_department}, 'om_hr_exit.om_hr_exit_action'),
        ('documents', 'bar', 'Documents to Renew by Type', 'document.document', TO_RENEW, 'type_id', by_department,
         'om_hr_document.om_document_action_hr'),
    ]
    for index, (key, chart_type, title, model, domain, group_by, matching, action) in enumerate(charts):
        x = (index % 2) * (HALF_WIDTH + GAP)
        y = 240 + (index // 2) * 290
        dashboard.odoo_chart(key, chart_type, title, model, '__count', [group_by], domain, x, y, HALF_WIDTH, 280,
                             field_matching=matching, action_xmlid=action)

    documents = workbook.odoo_list(
        'Documents to Renew', 'document.document', TO_RENEW,
        [('employee_id', 'Employee'), ('type_id', 'Type'), ('number', 'Number'), ('date_expiry', 'Expires On')],
        order_by=[('date_expiry', True)], field_matching=by_department)
    title_row = 37
    dashboard.set(0, title_row, label('Documents to Renew'), HEADER)
    dashboard.set(0, title_row + 1, '=ODOO.LIST(%s,20)' % documents)
    workbook.dump(os.path.join(FILES, 'talent_dashboard.json'))


if __name__ == '__main__':
    build_talent()
    print('Wrote', os.path.join(FILES, 'talent_dashboard.json'))
