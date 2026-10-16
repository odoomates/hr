{
    'name': 'HR Sign',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees sign their documents, and read and agree to the company policies or sign them',
    'description': 'The print templates of the employees name who signs among the employee, their manager or '
                   'coach, e.g. a contract signed by the employee and then the manager. The policies of the '
                   'company, such as the code of conduct or an NDA, are written in the editor or uploaded as a '
                   'PDF, and asked to the whole company, departments, job positions, tags or some employees: each '
                   'employee reads and agrees with one click, or signs it. A new version asks everyone again, the '
                   'new employees are asked too, and HR follows who answered. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_sign', 'om_hr_base'],
    'data': [
        'security/hr_sign_security.xml',
        'security/ir.access.csv',
        'data/hr_sign_data.xml',
        'report/policy_report.xml',
        'views/hr_policy_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
