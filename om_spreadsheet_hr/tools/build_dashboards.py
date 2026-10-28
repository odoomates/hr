#!/usr/bin/env python3
""" Write the Workforce dashboard of om_spreadsheet_hr into data/files.

    python3 om_spreadsheet_hr/tools/build_dashboards.py

The figures of the cards and of the months come from the OM.HR formulas of this module: they count the employees
under contract on a date from the contract versions, archived employees included, for the companies selected in the
company switcher. The charts and the list follow the Period and Department filters.
The builder is in om_spreadsheet_hr/tools, used at build time only: the module does not need Accounting.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'om_spreadsheet_hr', 'tools'))

from spreadsheet_builder import (  # noqa: E402
    GREEN, HEADER, INTEGER_FORMAT, PERCENT_FORMAT, RED, TEXT, Workbook, cards, dashboard_sheet, label,
)

FILES = os.path.join(os.path.dirname(HERE), 'data', 'files')

DATE_FORMAT = 'mm/dd/yyyy'
MONTH_FORMAT = 'mmm yyyy'
CARD_WIDTH = 190
GAP = 10
FULL_WIDTH = 5 * CARD_WIDTH + 4 * GAP
HALF_WIDTH = (FULL_WIDTH - GAP) // 2


def build_workforce():
    workbook = Workbook('hr_workforce')
    dashboard = dashboard_sheet(workbook)
    data = workbook.sheet('Data')
    period = workbook.date_filter('period', 'Period', 'this_year')
    department = workbook.relation_filter('department', 'Department', 'hr.department')

    rows = [
        ('Period', '=ODOO.FILTER.VALUE("Period")', DATE_FORMAT),
        ('End', '=IF(ISNUMBER(C1),MIN(C1,TODAY()),TODAY())', DATE_FORMAT),
        ('Start', '=IF(ISNUMBER(B1),B1,DATE(YEAR(TODAY()),1,1))', DATE_FORMAT),
        ('Departments', '=ODOO.FILTER.VALUE("Department")', None),
        ('Headcount', '=OM.HR.HEADCOUNT(B2,B4)', INTEGER_FORMAT),
        ('Headcount at start', '=OM.HR.HEADCOUNT(B3-1,B4)', INTEGER_FORMAT),
        ('Joiners', '=OM.HR.JOINERS(B3,B2,B4)', INTEGER_FORMAT),
        ('Leavers', '=OM.HR.LEAVERS(B3,B2,B4)', INTEGER_FORMAT),
        ('Average headcount', '=AVERAGE(B5,B6)', '0.0'),
        ('Turnover', '=IF(B9>0,B8/B9,0)', PERCENT_FORMAT),
        ('Average service (years)', '=OM.HR.TENURE(B2,B4)', '0.0'),
        ('Change of headcount', '=B5-B6', INTEGER_FORMAT),
    ]
    for row, (text, formula, fmt) in enumerate(rows):
        data.set(0, row, label(text), TEXT)
        data.set(1, row, formula, fmt=fmt)
    data.set(2, 0, None, fmt=DATE_FORMAT)

    # the months of the period, up to today
    first = 14
    for col, text in enumerate(['Month', 'Last day', 'Headcount', 'Joiners', 'Leavers']):
        data.set(col, first - 1, label(text), HEADER)
    for index in range(12):
        row, line = first + index, first + index + 1
        data.set(0, row, '=EDATE(DATE(YEAR($B$3),MONTH($B$3),1),%s)' % index, fmt=MONTH_FORMAT)
        data.set(1, row, '=MIN(EOMONTH(A%s,0),$B$2)' % line, fmt=DATE_FORMAT)
        data.set(2, row, '=IF(A%s>$B$2,"",OM.HR.HEADCOUNT(B%s,$B$4))' % (line, line), fmt=INTEGER_FORMAT)
        data.set(3, row, '=IF(A%s>$B$2,"",OM.HR.JOINERS(A%s,B%s,$B$4))' % (line, line, line), fmt=INTEGER_FORMAT)
        data.set(4, row, '=IF(A%s>$B$2,"",OM.HR.LEAVERS(A%s,B%s,$B$4))' % (line, line, line), fmt=INTEGER_FORMAT)
    last = first + 11
    data.col_sizes.update({0: 200, 1: 130, 2: 130, 3: 110, 4: 110})

    cards(dashboard, [
        ('headcount', 'Headcount', 'Data!B5', 'Data!B12', 'since the start of the period', GREEN, RED),
        ('joiners', 'Joiners', 'Data!B7', None, None, GREEN, RED),
        ('leavers', 'Leavers', 'Data!B8', None, None, RED, GREEN),
        ('turnover', 'Turnover', 'Data!B10', None, None, RED, GREEN),
        ('tenure', 'Service (Years)', 'Data!B11', None, None, GREEN, RED),
    ], CARD_WIDTH, per_row=5)

    dashboard.chart(
        'monthly', 'combo', 'Headcount, Joiners and Leavers by Month', data.range(0, first, 0, last),
        [(data.range(3, first, 3, last), 'Joiners', {'type': 'bar'}),
         (data.range(4, first, 4, last), 'Leavers', {'type': 'bar'}),
         (data.range(2, first, 2, last), 'Headcount', {'type': 'line'})],
        0, 120, FULL_WIDTH, 300)

    by_department = {department: ('department_id', 'many2one')}
    charts = [
        ('department', 'bar', 'Employees by Department', 'department_id'),
        ('job', 'bar', 'Employees by Job Position', 'job_id'),
        ('nationality', 'pie', 'Employees by Nationality', 'country_id'),
        ('type', 'pie', 'Employees by Type', 'employee_type_id'),
    ]
    for index, (key, chart_type, title, group_by) in enumerate(charts):
        x = (index % 2) * (HALF_WIDTH + GAP)
        y = 430 + (index // 2) * 290
        dashboard.odoo_chart(key, chart_type, title, 'hr.employee', '__count', [group_by], [], x, y, HALF_WIDTH, 280,
                             field_matching=by_department, action_xmlid='hr.open_view_employee_list_my')

    # the contracts ending in the period, below the charts
    ending = workbook.odoo_list(
        'Contracts Ending', 'hr.version',
        [('contract_date_end', '!=', False), ('employee_id.active', 'in', [True, False])],
        [('employee_id', 'Employee'), ('department_id', 'Department'), ('job_id', 'Job Position'),
         ('contract_date_end', 'Contract End')],
        order_by=[('contract_date_end', True)],
        field_matching={period: ('contract_date_end', 'date'), department: ('department_id', 'many2one')},
        context={'active_test': False})
    title_row = 46
    dashboard.set(0, title_row, label('Contracts Ending in the Period'), HEADER)
    dashboard.set(0, title_row + 1, '=ODOO.LIST(%s,20)' % ending)
    workbook.dump(os.path.join(FILES, 'workforce_dashboard.json'))


if __name__ == '__main__':
    build_workforce()
    print('Wrote', os.path.join(FILES, 'workforce_dashboard.json'))
