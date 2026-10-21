# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    made_in_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Made In',
        help='Country of origin for this line (e.g. Made in India). Shown on receipt and PO PDFs.',
    )

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.made_in_country_id:
            vals['made_in_country_id'] = self.made_in_country_id.id
        return vals

    def get_line_description(self):
        if self.order_id:
            return self.order_id.get_line_description(self)
        return self.name or ''

    def is_transfer_or_cash_handling_charge(self):
        """Check if this PO line is Transfer Charges or Cash Handling Charges."""
        self.ensure_one()
        product = self.product_id
        if product:
            code = (product.default_code or '').strip().upper()
            if code in ('CASH-HANDLING', 'TRANSFER-CHARGES') or 'CASH-HANDLING' in code or 'TRANSFER-CHARGES' in code:
                return True
            pname = (product.name or '').strip().upper()
            if 'CASH HANDLING' in pname or 'TRANSFER CHARGES' in pname:
                return True
            tmpl = getattr(product, 'product_tmpl_id', False)
            if tmpl:
                tname = (tmpl.name or '').strip().upper()
                if 'CASH HANDLING' in tname or 'TRANSFER CHARGES' in tname:
                    return True
        lname = (self.name or '').strip().upper()
        if 'CASH HANDLING' in lname or 'TRANSFER CHARGES' in lname:
            return True
        return False

