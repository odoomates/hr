{
    'name': 'HR Appraisals: 360 Feedback',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Peers, direct reports and others answer a survey about the employee; the employee reads the '
               'combined answers without the names',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_appraisal', 'survey'],
    'data': [
        'security/ir.access.csv',
        'data/survey_data.xml',
        'wizard/hr_appraisal_feedback_request_views.xml',
        'views/hr_appraisal_views.xml',
    ],
    'demo': ['demo/om_hr_appraisal_survey_demo.xml'],
    'images': ['static/description/banner.gif'],
}
