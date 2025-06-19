# -*- coding: utf-8 -*-
from odoo import api, fields, models

class CustomContact(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        action_id = options.get('action_id')
        contact_action = self.env.ref('contacts.action_contacts', raise_if_not_found=False)

        if action_id and contact_action and action_id != contact_action.id:
            if view_type in ('kanban', 'list', 'form'):
                for node in arch.xpath('//form | //kanban | //list'):
                    node.set('create', 'false')
        return arch, view

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True, help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True, help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
