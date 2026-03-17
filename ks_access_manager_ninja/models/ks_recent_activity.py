# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import fields, models


class KsRecentActivityLine(models.Model):
    _name = 'recent.activity'
    _description = 'Users Login/Logout Activity'

    ks_login_date = fields.Datetime('Login Date')
    ks_logout_date = fields.Datetime('Logout Date')
    ks_duration = fields.Char('Duration')
    ks_user_id = fields.Many2one('res.users', string='Users')
    ks_status = fields.Selection([('active', 'Active'), ('close', 'Closed')], string='Status')
    ks_session_id = fields.Char(string='Session Id')

    def ks_action_logout(self):
        """Admin can log out any user and evaluate the duration of their active session."""
        for rec in self:
            rec.ks_status = 'close'
            rec.ks_logout_date = datetime.now()

            # Calculate duration
            duration = rec.ks_logout_date - rec.ks_login_date
            total_seconds = int(duration.total_seconds())

            # Calculate days, hours, and minutes
            days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
            hours, remainder = divmod(remainder, 3600)  # 3600 seconds in an hour
            minutes, _ = divmod(remainder, 60)  # 60 seconds in a minute

            # Build duration string based on time components
            if days > 0:
                rec.ks_duration = f"{days} Day {hours} Hour {minutes} Minute"
            elif hours > 0:
                rec.ks_duration = f"{hours} Hour {minutes} Minute"
            else:
                rec.ks_duration = f"{minutes} Minute"

