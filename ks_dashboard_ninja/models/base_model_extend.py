# -*- coding: utf-8 -*-

from odoo import models, api


class BaseExtend(models.AbstractModel):
    _inherit = 'base'

    def _dn_has_active_channel(self):
        """
        Return True if at least one websocket client is subscribed to the
        'ks_notification' channel. We rely on the internal bus dispatcher
        to know current subscriptions and avoid queuing messages when no
        client is interested.
        """
        try:
            # Import here to avoid import cost during module loading
            from odoo.addons.bus.models.bus import dispatch
            channel_key = (self.env.cr.dbname, 'ks_notification')
            return bool(dispatch._channels_to_ws.get(channel_key))
        except Exception:
            # In doubt, don't send to avoid flooding the bus
            return False

    def _dn_is_auto_update_enabled(self):
        """
        Check if auto-update is enabled in settings.
        """
        return self.env['ir.config_parameter'].sudo().get_param('ks_dashboard_ninja.enable_auto_update', 'False').lower() == 'true'


    @api.model_create_multi
    def create(self, vals):
        recs = super(BaseExtend, self).create(vals)
        if (
                self._name in self.env['ks_dashboard_ninja.item'].dn_models_in_use()
                and self.env.user
                and self.env.user.has_group('base.group_user')
                and self._dn_is_auto_update_enabled()
                and self._dn_has_active_channel()
        ):
            self.env['bus.bus']._sendone('ks_notification', 'Update: Dashboard Items', {'model': self._name})
        return recs

    def unlink(self):
        recs = super(BaseExtend, self).unlink()
        if (
                self._name in self.env['ks_dashboard_ninja.item'].dn_models_in_use()
                and self.env.user
                and self.env.user.has_group('base.group_user')
                and self._dn_is_auto_update_enabled()
                and self._dn_has_active_channel()
        ):
            self.env['bus.bus']._sendone('ks_notification', 'Update: Dashboard Items', {'model': self._name})
        return recs

    def write(self, vals):
        recs = super(BaseExtend, self).write(vals)
        if (
                self._name in self.env['ks_dashboard_ninja.item'].dn_models_in_use()
                and self.env.user
                and self.env.user.has_group('base.group_user')
                and 'res.partner' not in self._name
                and self._dn_is_auto_update_enabled()
                and self._dn_has_active_channel()
        ):
            self.env['bus.bus']._sendone('ks_notification', 'Update: Dashboard Items', {'model': self._name})
        return recs