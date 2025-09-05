
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

    show_qc_tab = fields.Boolean(compute='_compute_show_qc_tab')

    def _compute_show_qc_tab(self):
        self.show_qc_tab = self.is_qc_done and self.picking_type_code == 'incoming'

    is_qc_done = fields.Boolean( string='QC check status', help="A boolean field to track the state of the QC.", tracking=True)


    def action_toggle_qc_button(self):

        message = ""
        if self.picking_type_code == 'incoming':    
            message = "QC passed — you may now validate the receipt."
        else:
            message = "QC passed — you may now validate the delivery."


        for picking in self:
            if not picking.is_qc_done:
                picking.is_qc_done = True

                if picking.is_qc_done and self.picking_type_code == 'incoming':
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
                        'message': message,
                        'sticky': True,
                    })

        # if self.picking_type_code == 'incoming':    
        #     return {
        #         "type": "ir.actions.client",
        #         "tag": "switch_to_qc_tab", 
        #         "params": {
        #             "tab_name": "Quality Check",
        #         },
        #     }


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