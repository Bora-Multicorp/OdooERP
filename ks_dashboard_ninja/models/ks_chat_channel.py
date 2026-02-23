# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import models, fields, _


class ChatChannel(models.Model):
    _inherit = 'discuss.channel'

    ks_dashboard_board_id = fields.Many2one('ks_dashboard_ninja.board')
    ks_dashboard_item_id = fields.Many2one('ks_dashboard_ninja.item')

    def ks_chat_wizard_channel_id(self, item_id, dashboard_id, **kwargs):
        channel_id = self.search_read(domain=[('ks_dashboard_item_id', '=', item_id)], fields=['id'], limit=1)

        if not channel_id:
            users = self.env['res.users'].search([('groups_id', 'in', self.env.ref('base.group_user').ids)]).mapped('partner_id.id')

            channel = self.create({
                'name': f"{kwargs.get('dashboard_name', 'Dashboard Name')} - {kwargs.get('item_name', 'Item Name')}",
                'ks_dashboard_board_id': dashboard_id,
                'ks_dashboard_item_id': item_id,
                'channel_member_ids': [(0, 0, {'partner_id': partner_id}) for partner_id in users]
            })

            notification = Markup('<div class="o_mail_notification">%s</div>') % _("created this channel.")
            channel.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")
            self.env.user._bus_send_store(channel)
            return channel.id

        return channel_id[0].get('id', False)
