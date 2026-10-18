from odoo import api, fields, models

from odoo.addons.om_hr_compensation.models.hr_version import BAND_POSITIONS


class HrMeritMatrix(models.Model):
    """ The raise suggested for a rating, by where the wage sits in its band: a better rating gets more, and a
    wage already high in its band gets less, so that the wages move towards the midpoint. """
    _name = 'hr.merit.matrix'
    _description = 'Merit Matrix'
    _order = 'rating_id, band_position'

    rating_id = fields.Many2one('hr.appraisal.rating', required=True, ondelete='cascade')
    band_position = fields.Selection(BAND_POSITIONS, string='In Band', required=True)
    percent = fields.Float(string='Raise (%)', digits=(16, 2))
    company_id = fields.Many2one('res.company', help='Leave empty to use it for all the companies.')

    _cell_uniq = models.Constraint('unique(rating_id, band_position, company_id)',
                                   'The merit matrix has one raise per rating and band position.')

    @api.model
    def _get_percent(self, rating, position, company):
        """ :return: the raise suggested, the one of the company first, else the shared one; None without one """
        cells = self.search([('rating_id', '=', rating.id), ('band_position', '=', position),
                             ('company_id', 'in', (company.id, False))], order='company_id')
        return cells[:1].percent if cells else None
