# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class KsApprovalConfirmationWizard(models.TransientModel):
    _name = 'ks.approval.confirmation.wizard'
    _description = 'KS Approval Confirmation Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_approver_names = fields.Char(
        string='Approvers',
        compute='_compute_approver_names',
        readonly=True,
        store=False,
    )

    @api.model
    def default_get(self, fields_list):
        """Compute approver names when wizard is created"""
        res = super().default_get(fields_list)
        po_id = self.env.context.get('default_ks_purchase_order_id')
        if po_id:
            po = self.env['purchase.order'].browse(po_id)
            if po.exists() and po._has_approval_config():
                try:
                    config = po._get_approval_config()
                    pm1_name = config.ks_confirm_pm1_id.name if config.ks_confirm_pm1_id else ''
                    pm2_name = config.ks_confirm_pm2_id.name if config.ks_confirm_pm2_id else ''
                    if pm1_name and pm2_name:
                        res['ks_approver_names'] = f"{pm1_name}, {pm2_name}"
                    elif pm1_name:
                        res['ks_approver_names'] = pm1_name
                    elif pm2_name:
                        res['ks_approver_names'] = pm2_name
                    else:
                        res['ks_approver_names'] = _('No approvers configured')
                except Exception:
                    res['ks_approver_names'] = _('No approvers configured')
        return res

    @api.depends('ks_purchase_order_id')
    def _compute_approver_names(self):
        """Compute the approver names from the PO configuration"""
        for record in self:
            if record.ks_purchase_order_id:
                try:
                    if not record.ks_purchase_order_id._has_approval_config():
                        record.ks_approver_names = _('No approvers configured')
                        continue
                    
                    config = record.ks_purchase_order_id._get_approval_config()
                    pm1_name = config.ks_confirm_pm1_id.name if config.ks_confirm_pm1_id else ''
                    pm2_name = config.ks_confirm_pm2_id.name if config.ks_confirm_pm2_id else ''
                    if pm1_name and pm2_name:
                        record.ks_approver_names = f"{pm1_name}, {pm2_name}"
                    elif pm1_name:
                        record.ks_approver_names = pm1_name
                    elif pm2_name:
                        record.ks_approver_names = pm2_name
                    else:
                        record.ks_approver_names = _('No approvers configured')
                except Exception as e:
                    record.ks_approver_names = _('No approvers configured')
            else:
                record.ks_approver_names = ''

    def action_confirm_send(self):
        """User confirms to send the approval request"""
        self.ensure_one()
        self.ks_purchase_order_id._ks_send_to_pending_approval()
        return {'type': 'ir.actions.act_window_close'}

