from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _create_picking(self):
        result = super()._create_picking()
        for order in self.filtered("ks_ecom_imported"):
            if order.picking_ids:
                order.picking_ids.write({"ks_ecom_po_reciept": True})
        return result

    ks_ecom_imported = fields.Boolean(
        string="Imported from E-com",
        copy=False,
        readonly=True,
    )
    ks_ecom_order_id = fields.Char(string="Order ID", copy=False, index=True)
    ks_ecom_source_file = fields.Char(string="Import File", copy=False, readonly=True)
    ks_ecom_refunded = fields.Boolean(
        string="E-com Refunded",
        copy=False,
        default=False,
        help="Set when refund has been processed via XLSX Refund Import (receipt return and/or bill reversal).",
    )
    ks_ecom_tag_ids = fields.Many2many(
        "ks.ecom.tag",
        "purchase_order_ks_ecom_tag_rel",
        "purchase_id",
        "tag_id",
        string="Tags",
        copy=False,
    )
    ks_ecom_info_ids = fields.One2many(
        "ks.ecom.purchase.info",
        "purchase_id",
        string="Imported E-com Information",
        copy=False,
    )

    def action_open_ecom_import_wizard(self):
        """Open XLSX import wizard from Purchase Order form."""
        action = self.env.ref("ks_ecom_purchase.action_ks_po_import_wizard").read()[0]
        action["context"] = dict(self.env.context, default_purchase_id=self.id if self else False)
        return action

    def action_open_receipt_import_wizard(self):
        """Open XLSX receipt import wizard from Purchase Order form."""
        action = self.env.ref("ks_ecom_purchase.action_po_receipt_import_wizard").read()[0]
        return action

    def action_open_refund_import_wizard(self):
        """Open XLSX refund import wizard from Purchase Order form."""
        action = self.env.ref("ks_ecom_purchase.action_po_refund_import_wizard").read()[0]
        return action


class KsEcomPurchaseInfo(models.Model):
    _name = "ks.ecom.purchase.info"
    _description = "E-com Purchase Imported Information"
    _order = "id"

    purchase_id = fields.Many2one("purchase.order", required=True, ondelete="cascade")
    field_key = fields.Char(string="Field", required=True)
    field_value = fields.Char(string="Value")

