{
    'name': 'Biometric Attendance Machine - TCP/UDP',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'ZKTeco and eSSL devices read by Odoo over the network (TCP/UDP port 4370): punches, users, clock',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_biometric'],
    'data': [
        'data/om_hr_biometric_zk_data.xml',
        'views/hr_biometric_device_views.xml',
    ],
    'images': ['static/description/banner.gif'],
}
