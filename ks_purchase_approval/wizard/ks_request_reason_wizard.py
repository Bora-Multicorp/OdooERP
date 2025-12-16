# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsRequestReasonWizard(models.TransientModel):
    _name = 'ks.request.reason.wizard'
    _description = 'KS Request Reason Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_request_type = fields.Selection([
        ('update', 'Update Request'),
        ('cancel', 'Cancellation Request'),
    ], string='Request Type', required=True)
    
    ks_reason = fields.Text(
        string='Reason',
        required=True,
        help='Please provide a reason for your request',
    )
    
    ks_request_type_label = fields.Char(
        string='Request Type Label',
        compute='_compute_request_type_label',
    )

    @api.depends('ks_request_type')
    def _compute_request_type_label(self):
        for record in self:
            if record.ks_request_type == 'update':
                record.ks_request_type_label = _('Update Request')
            elif record.ks_request_type == 'cancel':
                record.ks_request_type_label = _('Cancellation Request')
            else:
                record.ks_request_type_label = ''

    def action_submit_request(self):
        """Submit the request with the provided reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Please provide a reason for your request."))
        
        order = self.ks_purchase_order_id
        reason = self.ks_reason.strip()
        
        if self.ks_request_type == 'update':
            order.ks_do_request_update(reason)
        elif self.ks_request_type == 'cancel':
            order.ks_do_request_cancel(reason)
        else:
            raise UserError(_("Invalid request type."))
        
        return {'type': 'ir.actions.act_window_close'}
