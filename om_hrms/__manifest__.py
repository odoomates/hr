{
    'name': 'Odoo Mates HR',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'HRMS for Odoo 20 Community: Payroll, Loans, Exit, Gratuity, Documents, Appraisals, Shifts, '
               'Approvals, Employee Portal',
    'description': 'Odoo Mates HR, the HR suite for Odoo 20 Community, with or without Accounting: '
                   'payroll, paid on the schedule or on the attendances, employee loans and salary advances, '
                   'bonuses, commissions and fines, overtime pay and pre-approval, lateness penalties, shift '
                   'planning with rosters, rotations, open shifts and swaps, approval flows for HR documents and '
                   'for the buttons of any app, HR requests, resignations and terminations with their clearance, '
                   'end of service gratuity and final settlement with leave encashment, employee documents such '
                   'as passports and visas with expiry reminders, salary and experience certificates and NOC '
                   'printed from templates, appraisals and probation reviews, employee assets, bank transfer '
                   'files, HR and payroll dashboards, birthday and anniversary reminders, and self-service for '
                   'the employees in My HR and on the portal. '
                   'Installing this module installs all of them. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': [
        'om_hr_base',
        'om_approval',
        'om_hr_approval',
        'om_hr_payroll',
        'om_hr_loan',
        'om_hr_loan_payroll',
        'om_hr_exit',
        'om_hr_gratuity',
        'om_hr_exit_payroll',
        'om_document',
        'om_hr_document',
        'om_print_template',
        'om_print_template_document',
        'om_hr_certificate',
        'om_hr_appraisal',
        'om_hr_overtime_payroll',
        'om_hr_asset',
        'om_hr_asset_exit',
        'om_hr_asset_payroll',
        'om_file_layout',
        'om_hr_payroll_export',
        'om_hr_portal',
        'om_hr_portal_payslip',
        'om_hr_portal_leave',
        'om_hr_portal_loan',
        'om_hr_portal_certificate',
        'om_hr_portal_document',
        'om_hr_portal_asset',
        'om_hr_portal_appraisal',
        'om_hr_portal_exit',
        'om_spreadsheet_hr',
        'om_spreadsheet_hr_payroll',
        'om_spreadsheet_hr_time',
        'om_spreadsheet_hr_talent',
        'om_hr_reminder',
        'om_hr_payroll_adjustment',
        'om_hr_portal_adjustment',
        'om_hr_lateness',
        'om_hr_lateness_payroll',
        'om_hr_shift',
        'om_hr_portal_shift',
        'om_hr_shift_payroll',
        'om_hr_overtime_request',
        'om_hr_announcement',
        'om_hr_portal_announcement',
    ],
    'images': ['static/description/banner.gif'],
    'application': True,
    'sequence': '1',
}
