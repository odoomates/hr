{
    'name': 'HR Compensation: Appraisals',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'The merit cycles show the last rating of each employee and suggest their raise from a merit matrix',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_compensation', 'om_hr_appraisal'],
    'data': [
        'security/ir.access.csv',
        'data/hr_merit_matrix_data.xml',
        'views/hr_merit_matrix_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
