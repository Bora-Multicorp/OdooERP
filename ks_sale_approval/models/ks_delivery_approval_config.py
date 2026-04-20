# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KsDeliveryApprovalConfig(models.Model):
    _name = 'ks.delivery.approval.config'
    _description = 'KS Delivery Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        default='Global Delivery Approval Configuration',
        required=True,
    )

    ks_approval_mode = fields.Selection([
        ('single', 'Single PM Approval'),
        ('dual', 'Two PM Approval (Both Required)'),
    ], string='Approval Mode', required=True, default='single',
       help='Single: One PM approval allows validation.\n'
            'Dual: Both PM1 and PM2 must approve.')

    ks_validate_pm1_ids = fields.Many2many(
        'res.users',
        'ks_delivery_approval_pm1_rel',
        'config_id', 'user_id',
        string='Validation Approvers PM1',
        required=True,
    )
    ks_validate_pm2_ids = fields.Many2many(
        'res.users',
        'ks_delivery_approval_pm2_rel',
        'config_id', 'user_id',
        string='Validation Approvers PM2',
    )

    active = fields.Boolean(default=True)

    @api.constrains('active')
    def _check_single_active_config(self):
        for record in self:
            if record.active:
                other = self.search([('active', '=', True), ('id', '!=', record.id)], limit=1)
                if other:
                    raise ValidationError(_(
                        'Only one active delivery approval configuration is allowed! '
                        'Please deactivate "%s" first.'
                    ) % other.name)

    @api.constrains('ks_approval_mode', 'ks_validate_pm2_ids')
    def _check_dual_approval_pms(self):
        for record in self:
            if record.ks_approval_mode == 'dual' and not record.ks_validate_pm2_ids:
                raise ValidationError(_(
                    'Validation Approvers PM2 are required when using Two PM Approval mode!'
                ))

    @api.model
    def get_config(self):
        return self.search([('active', '=', True)], limit=1)

    def get_all_pm_users(self):
        self.ensure_one()
        return self.ks_validate_pm1_ids | self.ks_validate_pm2_ids

    def is_dual_approval(self):
        self.ensure_one()
        return self.ks_approval_mode == 'dual'
