# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductSuspensionWizard(models.TransientModel):
    _name = 'product.suspend.wizard'
    _description = 'Product suspend confirmation wizard'

    product_id = fields.Many2one('product.template', string="Suspenstion for Product Confirmation")

    remark = fields.Char('Remark', required=True)

    def action_done(self):
        self.ensure_one()

        self.product_id.suspend_approval_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}
