from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ks_ecom_imported = fields.Boolean(
        string="Imported from E-com",
        copy=False,
        readonly=True,
    )
    ks_ecom_order_id = fields.Char(string="E-com Order ID", copy=False, index=True)
    ks_ecom_source_file = fields.Char(string="Import File", copy=False, readonly=True)
    ks_ecom_tag_ids = fields.Many2many(
        "ks.ecom.tag",
        "sale_order_ks_ecom_tag_rel",
        "sale_id",
        "tag_id",
        string="Tags",
        copy=False,
    )
    ks_ecom_info_ids = fields.One2many(
        "ks.ecom.sale.info",
        "sale_id",
        string="Imported E-com Information",
        copy=False,
    )

    def action_open_ecom_sale_import_wizard(self):
        """Open XLSX import wizard from Sale Order list."""
        action = self.env.ref("ks_ecom_sales.action_ks_so_import_wizard").read()[0]
        return action


class KsEcomSaleInfo(models.Model):
    _name = "ks.ecom.sale.info"
    _description = "E-com Sale Imported Information"
    _order = "id"

    sale_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    field_key = fields.Char(string="Field", required=True)
    field_value = fields.Char(string="Value")
