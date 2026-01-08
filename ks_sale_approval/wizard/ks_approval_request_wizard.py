# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsApprovalRequestWizard(models.TransientModel):
    _name = 'ks.sale.approval.request.wizard'
    _description = 'KS Sale Approval Request Wizard'

    ks_sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
    )
    ks_approval_recipients = fields.Html(
        string='Approval Recipients',
        compute='_compute_approval_recipients',
        readonly=True,
    )

    @api.depends('ks_sale_order_id')
    def _compute_approval_recipients(self):
        """Compute and display which PMs will receive the approval request"""
        for wizard in self:
            if not wizard.ks_sale_order_id:
                wizard.ks_approval_recipients = ''
                continue
            
            order = wizard.ks_sale_order_id
            if not order._has_approval_config():
                wizard.ks_approval_recipients = _('<p>No approval configuration found.</p>')
                continue
            
            config = order._get_approval_config()
            recipients_html = '<div class="alert alert-info">'
            recipients_html += '<h5><strong>Approval Request will be sent to:</strong></h5>'
            recipients_html += '<ul>'
            
            # Get PM users for confirmation
            pm1 = config.ks_confirm_pm1_id
            pm2 = config.ks_confirm_pm2_id
            
            if pm1:
                recipients_html += f'<li><strong>PM1:</strong> {pm1.name} ({pm1.login})</li>'
            
            if pm2:
                recipients_html += f'<li><strong>PM2:</strong> {pm2.name} ({pm2.login})</li>'
            
            if config.is_dual_approval():
                recipients_html += '</ul>'
                recipients_html += '<p class="mt-2"><strong>Note:</strong> Both PM1 and PM2 approval is required.</p>'
            else:
                recipients_html += '</ul>'
                recipients_html += '<p class="mt-2"><strong>Note:</strong> PM1 approval is required.</p>'
            
            recipients_html += '</div>'
            wizard.ks_approval_recipients = recipients_html

    def action_confirm_request(self):
        """Proceed with sending the approval request"""
        self.ensure_one()
        order = self.ks_sale_order_id
        order._ks_send_to_approval_pending()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel the approval request - do nothing"""
        return {'type': 'ir.actions.act_window_close'}

