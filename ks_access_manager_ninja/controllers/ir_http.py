# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _authenticate(cls, endpoint):
        """
        Override method to trace recent user activity (Login-Logout).
        """
        result = super(IrHttp, cls)._authenticate(endpoint=endpoint)

        user_id = request.session.uid
        if user_id:
            cls.create_recent_activity(user_id)

        return result

    @classmethod
    def create_recent_activity(cls, user_id):
        """
        Create a recent activity record for the logged-in user.
        """
        session_id = request.session.sid
        activity_pool = request.env['recent.activity'].sudo()
        activity = activity_pool.search([('ks_session_id', '=', session_id)])

        if not activity:
            activity_pool.create({
                'ks_status': 'active',
                'ks_user_id': user_id,
                'ks_duration': 'Logged in',
                'ks_session_id': session_id,
                'ks_login_date': datetime.now(),
            })

        # TODO : need to check all relavant cases for this line i belive we can remove this code (Nimesh Jethva)
        if activity.filtered(lambda act: act.ks_status == 'close'):
            request.session.logout(keep_db=True)
