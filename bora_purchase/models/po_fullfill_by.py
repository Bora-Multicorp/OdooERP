from odoo import models, fields, api

class PurchaseOrderInherited(models.Model):
    _inherit = 'purchase.order'

    fulfillment_by = fields.Selection([
        ('bora', 'Bora'),
        ('vendor', 'Vendor')
    ], string="Fulfillment By", required=True, default='vendor')

    delivery_partner = fields.Many2one("delivery.partners",  string="Delivery Partner")


    @api.onchange("fulfillment_by")
    def _onchange_fulfillment_by(self):
        for order in self:
            if order.fulfillment_by == "vendor":
                order.delivery_partner = False
                print('Delivery partner reset to False')


    # This for UI
    @api.onchange("partner_id", "company_id")
    def _onchange_partner_id(self):
        all_companies = self.env['res.company'].search([])
        bora_partners = all_companies.mapped('partner_id')
        for order in self:
            if order.partner_id in bora_partners:
                order.fulfillment_by = "bora"
            else:
                order.fulfillment_by = "vendor"



    # Below methos for re-ordering rules
    def _get_fulfillment_by(self, partner):
        all_companies = self.env['res.company'].search([])
        bora_partners = all_companies.mapped('partner_id')
        return "bora" if partner in bora_partners else "vendor"

    @api.model
    def create(self, vals):
        if not vals.get("fulfillment_by") and vals.get("partner_id"):
            partner = self.env["res.partner"].browse(vals["partner_id"])
            vals["fulfillment_by"] = self._get_fulfillment_by(partner)
        return super().create(vals)
    
    def write(self, vals):
        res = super().write(vals)
        if "partner_id" in vals:  # vendor changed
            for order in self:
                order.fulfillment_by = self._get_fulfillment_by(order.partner_id)
        return res




