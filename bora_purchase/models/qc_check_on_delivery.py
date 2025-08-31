
# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError
from .utility import to_unicode_bold

class QACheckForDelivery(models.Model):
    _inherit = 'stock.picking'

    is_model_or_color_not_match = fields.Boolean()
    qty_didnt_match = fields.Boolean()
    boxes_are_damaged = fields.Boolean()
    activated_items_received = fields.Boolean()

    a_purchase_order = fields.Boolean(
        string='Is Purchase Order',
        compute='_compute_is_purchase_order'
    )

    def _compute_is_purchase_order(self):
        for record in self:
            record.a_purchase_order = bool(record.purchase_id)

    is_qc_done = fields.Boolean(
        string='QC check status',
        help="A boolean field to track the state of the QC.",
        tracking=True
    )

    def action_toggle_qc_button(self):

        for picking in self:
            if not picking.is_qc_done:
                picking.is_qc_done = not picking.is_qc_done

                if picking.is_qc_done and picking.a_purchase_order:
                    self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': '',
                        'message': f"Please check {to_unicode_bold('Quality Check')} tab and confirm QC status before validating the delivery.",
                        'sticky': True,
                    })
                else:
                    self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': '',
                        'message': "QC passed — you may now validate the receipt.",
                        'sticky': True,
                    })

        return {
            "type": "ir.actions.client",
            "tag": "switch_to_qc_tab", 
            "params": {
                "tab_name": "Quality Check",
            },
        }



    def button_validate(self):
        if not self.is_qc_done:
            raise UserError("Please confirm QC status.")
        return super().button_validate()




class ResetQCSatus(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):

        original_picking_ids = self.pick_ids.ids

        res = super().process()
        
        backorder_pickings = self.env['stock.picking'].search([
            ('backorder_id', 'in', original_picking_ids)
        ])

        for picking in backorder_pickings:
            picking.is_qc_done = False
            picking.is_model_or_color_not_match = False
            picking.qty_didnt_match = False
            picking.boxes_are_damaged = False
            picking.activated_items_received = False
                        
        return res