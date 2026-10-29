# -*- coding:utf-8 -*-

from pytz import utc

from odoo import models


class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"

    def list_leaves(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a list of tuples (day, hours, resource.calendar.leaves)
            for each leave in the calendar.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)

        attendances = calendar._attendance_intervals_batch(from_datetime, to_datetime, resource)[resource.id]
        leaves = calendar._leave_intervals_batch(from_datetime, to_datetime, resource, domain)[resource.id]
        result = []
        for start, stop, leave in (leaves & attendances):
            if len(leave) == 1:
                result.append((start.date(), (stop - start).total_seconds() / 3600, leave))
                continue
            # time off following each other or overlapping come merged in one interval: give each its own part
            # of it, an hour that two of them cover going to the first one
            cursor = start
            for record in leave.sorted('date_from'):
                record_start = max(cursor, record.date_from.replace(tzinfo=utc))
                record_stop = min(stop, record.date_to.replace(tzinfo=utc))
                if record_stop > record_start:
                    result.append((start.date(), (record_stop - record_start).total_seconds() / 3600, record))
                    cursor = record_stop
        return result
