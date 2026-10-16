from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalAnnouncement(HrPortal):

    def _announcement_lines(self):
        """ :return: the recipient lines of the employee, on the published announcements """
        employee = self._employee()
        return request.env['hr.announcement.read'].sudo().search(
            [('employee_id', '=', employee.id), ('announcement_id.state', '=', 'published')]).sorted(
            lambda line: (not line.announcement_id.pinned, bool(line.read_date),
                          -line.announcement_id.date_start.timestamp()))

    def _announcement_line(self, announcement_id):
        line = self._announcement_lines().filtered(lambda item: item.announcement_id.id == announcement_id)
        if not line:
            raise NotFound()
        return line

    @http.route('/my/hr/announcements', type='http', auth='user', website=True)
    def hr_announcements(self, **kwargs):
        return request.render('om_hr_portal_announcement.portal_my_announcements', self._values(
            'hr_announcements', lines=self._announcement_lines(), om_section='Announcements'))

    @http.route('/my/hr/announcements/<int:announcement_id>', type='http', auth='user', website=True)
    def hr_announcement(self, announcement_id, **kwargs):
        line = self._announcement_line(announcement_id)
        line.announcement_id._mark_read()
        return request.render('om_hr_portal_announcement.portal_my_announcement', self._values(
            'om_hr_announcement', line=line, announcement=line.announcement_id, om_section='Announcements',
            om_section_url='/my/hr/announcements', om_record=line.announcement_id.name))

    @http.route('/my/hr/announcements/<int:announcement_id>/acknowledge', type='http', auth='user', website=True,
                methods=['POST'])
    def hr_announcement_acknowledge(self, announcement_id, **post):
        line = self._announcement_line(announcement_id)
        # as the super user, still the employee: their own line is acknowledged
        line.announcement_id.action_acknowledge()
        return request.redirect('/my/hr/announcements/%s' % announcement_id)
