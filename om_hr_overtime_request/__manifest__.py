{
    'name': 'Overtime Pre-Approval',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Authorise overtime in advance; overtime beyond it waits for the manager to accept or reject',
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
    'demo': ['demo/om_hr_overtime_request_demo.xml'],
    'images': ['static/description/banner.gif'],
}
