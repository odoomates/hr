{
    'name': 'HR Compensation',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Salary grades and bands, compa-ratio, and merit cycles with department budgets turning the raises '
               'into contract versions',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'mail'],
    'data': [
        'security/ir.access.csv',
        'views/hr_salary_grade_views.xml',
        'views/hr_version_views.xml',
        'views/hr_merit_cycle_views.xml',
        'views/menu.xml',
    ],
    'demo': ['demo/om_hr_compensation_demo.xml'],
    'images': ['static/description/banner.gif'],
    'application': True,
}
