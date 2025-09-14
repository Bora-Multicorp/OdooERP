from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    create_date = fields.Datetime(string="PO Date", readonly=False, required=True)


    def create(self, vals):
        if vals.get("create_date"):
            # Force user-entered date
            self = super().create(vals)
            self.with_context(skip_update=True).write({"create_date": vals["create_date"]})
            return self
        return super().create(vals)

    def write(self, vals):
        if "create_date" in vals:
            self.env.cr.execute(
                "UPDATE purchase_order SET create_date=%s WHERE id IN %s",
                (vals["create_date"], tuple(self.ids)),
            )
            # reload record to avoid cache mismatch
            self.invalidate_recordset()
            return True
        return super().write(vals)
    