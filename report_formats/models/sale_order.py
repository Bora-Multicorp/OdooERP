from odoo import models, fields, api
from datetime import datetime

class SaleOrder(models.Model):
    _inherit = "sale.order"


    dispatch_id = fields.Char(string="Dispatch through")

    buyer_ref_no = fields.Char(
        string="Buyer's Ref./Order No.",
        readonly=True,
        copy=False
    )

    voucher_no = fields.Char(
        string="Voucher No.",
        readonly=True,
        copy=False
    )



    @api.model
    def create(self, vals):
        if not vals.get('buyer_ref_no'):
            # Get company name abbreviation
            company = self.env.company
            company_abbr = ''.join([word[0].upper() for word in company.name.split() if word])

            # Current year last two digits
            year_suffix = datetime.now().strftime('%y')

            # Auto increment sequence
            sequence = self.env['ir.sequence'].next_by_code('sale.order.buyer.ref') or '000'

            # Final format: {COMPANY_ABBR}PI{YY}/{SEQ}
            vals['buyer_ref_no'] = f"{company_abbr}PI{year_suffix}/{sequence}"
        if not vals.get('voucher_no'):
            # Get company name abbreviation
            company = self.env.company
            company_abbr = ''.join([word[0].upper() for word in company.name.split() if word])

            # Current year last two digits
            year_suffix = datetime.now().strftime('%y')

            # Auto increment sequence
            sequence = self.env['ir.sequence'].next_by_code('sale.order.voucher.no') or '000'

            # Final format: {COMPANY_ABBR}PI{YY}/{SEQ}
            vals['voucher_no'] = f"{company_abbr}PI{year_suffix}/{sequence}"

        return super(SaleOrder, self).create(vals)
