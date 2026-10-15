{
    'name': 'Overtime Pre-Approval',
    'version': '1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Authorise overtime in advance; overtime beyond it waits for the manager to accept or reject',
    'description': 'Employees or their managers ask for overtime in advance, approved along a flow. With '
                   'pre-approval on, the overtime the time rules of the Attendances app create is accepted up to the '
                   'approved hours of the day; beyond, it waits for the manager, who accepts or rejects it. Only the '
                   'accepted overtime is validated, and paid with Overtime in Payroll. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'hr_attendance', 'om_hr_approval'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_overtime_request_data.xml',
        'views/om_hr_overtime_request_views.xml',
    ],
    'images': ['static/description/banner.gif'],
}
