from odoo import fields, models, tools


class HrBiometricDaily(models.Model):
    """ The punches of each employee per day, the day being the one on the clock of the device. """
    _name = 'hr.biometric.daily'
    _description = 'Daily Biometric Attendance'
    _auto = False
    _order = 'date desc, employee_id'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    date = fields.Date(readonly=True)
    first_punch = fields.Datetime(readonly=True)
    last_punch = fields.Datetime(readonly=True)
    punch_count = fields.Integer(string='Punches', readonly=True, aggregator='sum')
    span_hours = fields.Float(string='First to Last (Hours)', readonly=True, aggregator='avg',
                              help='Time between the first and the last punch of the day.')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_biometric_daily AS (
                SELECT MIN(log.id) AS id,
                       log.employee_id,
                       log.company_id,
                       (log.timestamp AT TIME ZONE 'UTC' AT TIME ZONE device.timezone)::date AS date,
                       MIN(log.timestamp) AS first_punch,
                       MAX(log.timestamp) AS last_punch,
                       COUNT(*) AS punch_count,
                       EXTRACT(EPOCH FROM MAX(log.timestamp) - MIN(log.timestamp)) / 3600.0 AS span_hours
                  FROM hr_biometric_log log
                  JOIN hr_biometric_device device ON device.id = log.device_id
                 WHERE log.state = 'done' AND log.employee_id IS NOT NULL
              GROUP BY log.employee_id, log.company_id,
                       (log.timestamp AT TIME ZONE 'UTC' AT TIME ZONE device.timezone)::date
            )
        """)
