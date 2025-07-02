# -*- coding: utf-8 -*-
from email.policy import default

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

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True,
                                  help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True,
                                          help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    # Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Is Vendor?", tracking=True)
    is_customer = fields.Boolean(string="Is Customer?", tracking=True)
    is_kyc = fields.Boolean(string="Is KYC?", tracking=True)
    is_approved = fields.Boolean(string="Is Approved?", tracking=True)
    deadline = fields.Date('KYC Deadline', tracking=True)

    kyc_details = fields.One2many('res.partner.kyc.approval', 'partner_id', string="KYC Details", tracking=True)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_approved') is True:
            for record in self:
                if record.is_vendor:
                    record.supplier_rank = (record.supplier_rank or 0) + 1
                if record.is_customer:
                    record.customer_rank = (record.customer_rank or 0) + 1
        return res

    def confirm_rekyc(self):
        self.write({'is_kyc': False, 'is_approved': False, 'deadline': False})
        if self.is_vendor:
             self.write({'supplier_rank': 0})
        if self.is_customer:
             self.write({'customer_rank': 0})

