# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorApprovalConfig(models.Model):
    _name = "vendor.approval.config"
    _description = "Vendor Approval Settings"
    _rec_name = 'user_id'

    sequence = fields.Integer(string='Sequence', required=True)
    user_id = fields.Many2one('res.users', string='Approval User', required=True)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approval user must be unique.'),
        ('unique_sequence', 'unique(sequence)', 'Each sequence must be unique.'),
    ]

    @api.model
    def create(self, vals):
        if not vals.get('sequence'):
            seq_str = self.env['ir.sequence'].next_by_code('vendor.approval.config')
            try:
                vals['sequence'] = int(seq_str)
            except (ValueError, TypeError):
                raise ValidationError(_("Failed to generate a valid sequence number."))

        if int(vals['sequence']) <= 0:
            raise ValidationError(_("Sequence must be a positive number."))

        if vals.get('user_id') and self.search([('user_id', '=', vals['user_id'])]):
            raise ValidationError(_("This user is already added to the approval list."))

        if self.search([('sequence', '=', vals['sequence'])]):
            raise ValidationError(_("This sequence number is already used. Please choose a different one."))

        return super().create(vals)

    def write(self, vals):
        if vals.get('sequence') in [0]:
            raise ValidationError(_("Sequence must be a non-zero positive number."))

        if vals.get('user_id'):
            existing_user = self.search([
                ('user_id', '=', vals['user_id']),
                ('id', '!=', self.id)
            ])
            if existing_user:
                raise ValidationError(_("This user is already added to the approval list."))

        if vals.get('sequence'):
            existing_seq = self.search([
                ('sequence', '=', vals['sequence']),
                ('id', '!=', self.id)
            ])
            if existing_seq:
                raise ValidationError(_("This sequence number is already used. Please choose a different one."))

        return super(VendorApprovalConfig, self).write(vals)







