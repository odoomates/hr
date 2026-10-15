#!/usr/bin/env python3
""" Write the Payroll dashboard of om_spreadsheet_hr_payroll into data/files.

    python3 om_spreadsheet_hr_payroll/tools/build_dashboards.py

It reads the Payroll Analysis of om_hr_payroll: the lines of the confirmed payslips, the refunds counted negative,
with the department and the job of their contract. Everything follows the Period and Department filters.
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

MODEL = 'hr.payslip.analysis'
DONE = [['state', '=', 'done']]
DATE_FORMAT = 'mm/dd/yyyy'
MONTH_FORMAT = 'mmm yyyy'
AMOUNT_FORMAT = '#,##0'
CARD_WIDTH = 190
GAP = 10
FULL_WIDTH = 5 * CARD_WIDTH + 4 * GAP
HALF_WIDTH = (FULL_WIDTH - GAP) // 2


def build_payroll():
    workbook = Workbook('hr_payroll')
    dashboard = dashboard_sheet(workbook)
    data = workbook.sheet('Data')
    period = workbook.date_filter('period', 'Period', 'this_year')
    department = workbook.relation_filter('department', 'Department', 'hr.department')
    matching = {period: ('date', 'date'), department: ('department_id', 'many2one')}

    by_code = workbook.pivot('Pay by Rule Code', MODEL, DONE, ['total'], rows=['code'], field_matching=matching)
    paid = workbook.pivot('Employees Paid', MODEL, DONE + [['code', '=', 'NET']], ['employee_count'],
                          field_matching=matching)
    by_month = workbook.pivot('Pay by Month', MODEL, DONE + [['code', 'in', ['GROSS', 'NET']]], ['total'],
                              rows=[('date', 'month')], columns=['code'], field_matching=matching)
    earners = workbook.pivot('Top Earners', MODEL, DONE + [['code', '=', 'GROSS']], ['total'], rows=['employee_id'],
                             field_matching=matching, sorted_column=('total', 'desc'))

    rows = [
        ('Period', '=ODOO.FILTER.VALUE("Period")', DATE_FORMAT),
        ('Start', '=IF(ISNUMBER(B1),B1,DATE(YEAR(TODAY()),1,1))', DATE_FORMAT),
        ('Gross', '=0+PIVOT.VALUE(%s,"total","code","GROSS")' % by_code, AMOUNT_FORMAT),
        ('Net', '=0+PIVOT.VALUE(%s,"total","code","NET")' % by_code, AMOUNT_FORMAT),
        ('Employees paid', '=0+PIVOT.VALUE(%s,"employee_count")' % paid, INTEGER_FORMAT),
        ('Average gross', '=IF(B5>0,B3/B5,0)', AMOUNT_FORMAT),
        ('Overtime', '=0+PIVOT.VALUE(%s,"total","code","OVERTIME")' % by_code, AMOUNT_FORMAT),
        ('Loan deductions', '=0-PIVOT.VALUE(%s,"total","code","LOAN")' % by_code, AMOUNT_FORMAT),
    ]
    for row, (text, formula, fmt) in enumerate(rows):
        data.set(0, row, label(text), TEXT)
        data.set(1, row, formula, fmt=fmt)
    data.set(2, 0, None, fmt=DATE_FORMAT)

    first = 12
    for col, text in enumerate(['Month', 'Gross', 'Net']):
        data.set(col, first - 1, label(text), HEADER)
    for index in range(12):
        row, line = first + index, first + index + 1
        data.set(0, row, '=EDATE(DATE(YEAR($B$2),MONTH($B$2),1),%s)' % index, fmt=MONTH_FORMAT)
        key = 'TEXT(A%s,"mm/yyyy")' % line
        data.set(1, row, '=0+PIVOT.VALUE(%s,"total","date:month",%s,"code","GROSS")' % (by_month, key),
                 fmt=AMOUNT_FORMAT)
        data.set(2, row, '=0+PIVOT.VALUE(%s,"total","date:month",%s,"code","NET")' % (by_month, key),
                 fmt=AMOUNT_FORMAT)
    last = first + 11
    data.col_sizes.update({0: 200, 1: 130, 2: 130})

    cards(dashboard, [
        ('gross', 'Gross Pay', 'Data!B3', None, None, GREEN, RED),
        ('net', 'Net Pay', 'Data!B4', None, None, GREEN, RED),
        ('paid', 'Employees Paid', 'Data!B5', None, None, GREEN, RED),
        ('average', 'Average Gross', 'Data!B6', None, None, GREEN, RED),
        ('overtime', 'Overtime Paid', 'Data!B7', None, None, RED, GREEN),
    ], CARD_WIDTH, per_row=5)

    dashboard.chart(
        'monthly', 'bar', 'Gross and Net Pay by Month', data.range(0, first, 0, last),
        [(data.range(1, first, 1, last), 'Gross', None), (data.range(2, first, 2, last), 'Net', None)],
        0, 120, FULL_WIDTH, 300)

    charts = [
        ('department', 'bar', 'Gross Pay by Department', DONE + [['code', '=', 'GROSS']], 'department_id'),
        ('category', 'bar', 'Pay by Category', DONE + [['category_id.code', 'in', ['BASIC', 'ALW', 'DED']]],
         'category_id'),
        ('deductions', 'bar', 'Deductions by Rule', DONE + [['category_id.code', '=', 'DED']], 'salary_rule_id'),
        ('job', 'bar', 'Gross Pay by Job Position', DONE + [['code', '=', 'GROSS']], 'job_id'),
    ]
    for index, (key, chart_type, title, domain, group_by) in enumerate(charts):
        x = (index % 2) * (HALF_WIDTH + GAP)
        y = 430 + (index // 2) * 290
        dashboard.odoo_chart(key, chart_type, title, MODEL, 'total', [group_by], domain, x, y, HALF_WIDTH, 280,
                             field_matching=matching, action_xmlid='om_hr_payroll.action_hr_payslip_analysis')

    title_row = 46
    dashboard.set(0, title_row, label('Top Earners of the Period (Gross)'), HEADER)
    dashboard.set(0, title_row + 1, '=PIVOT(%s,10,FALSE,FALSE)' % earners)
    workbook.dump(os.path.join(FILES, 'payroll_dashboard.json'))


if __name__ == '__main__':
    build_payroll()
    print('Wrote', os.path.join(FILES, 'payroll_dashboard.json'))
