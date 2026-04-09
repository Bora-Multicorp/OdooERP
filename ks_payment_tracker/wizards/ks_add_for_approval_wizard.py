# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsAddForApprovalWizard(models.TransientModel):
    _name = 'ks.add.for.approval.wizard'
    _description = 'Add Purchase Orders for Payment Approval'

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        'ks_add_approval_wizard_po_rel',
        'wizard_id',
        'po_id',
        string='Purchase Orders',
        readonly=True,
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Assigned Approver',
        required=True,
        domain=[('share', '=', False)],   # internal users only
        help='This user will be the only one who can approve the created payment request.',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['purchase_order_ids'] = [(6, 0, active_ids)]
        return res

    def action_confirm(self):
        """Validate selected POs and create vendor.payment.approval.request records,
        then redirect to the newly created record(s).
        """
        orders = self.purchase_order_ids
        if not orders:
            raise UserError(_('No Purchase Orders selected.'))

        invalid = orders.filtered(lambda o: o.state not in ('purchase', 'done'))
        if invalid:
            raise UserError(_(
                'Only confirmed or locked Purchase Orders can be added for approval. '
                'Invalid orders: %s'
            ) % ', '.join(invalid.mapped('name')))

        ApprovalRequest = self.env['vendor.payment.approval.request']
        created = ApprovalRequest.browse()
        for order in orders:
            has_bill = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted'
            )
            approval_type = 'with_bill' if has_bill else 'without_bill'
            request = ApprovalRequest.create({
                'purchase_order_id': order.id,
                'approval_type': approval_type,
                'assigned_approver_id': self.approver_id.id,
            })
            created |= request

        if not created:
            raise UserError(_('No approval requests could be created.'))

        action = self.env['ir.actions.act_window']._for_xml_id(
            'ks_purchase_advance_payment.action_vendor_payment_approval_request'
        )
        if len(created) == 1:
            action['res_id'] = created.id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        else:
            action['domain'] = [('id', 'in', created.ids)]
            action['view_mode'] = 'list,form'
        return action
