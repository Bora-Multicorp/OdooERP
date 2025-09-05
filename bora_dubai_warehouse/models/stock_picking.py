from odoo import models, api, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    def _invoice_paid_hook(self):
        # keep Odoo’s default behavior
        res = super()._invoice_paid_hook()

        for move in self:
            if move.move_type != "out_invoice":
                continue  # only customer invoices

            # Find related SOs from invoice lines
            sale_orders = move.invoice_line_ids.sale_line_ids.order_id
            for so in sale_orders:
                # Get all related invoices
                invoices = so.invoice_ids.filtered(
                    lambda inv: inv.move_type == "out_invoice" and inv.state == "posted"
                )

                # Check if all invoices are paid
                all_paid = invoices and all(inv.payment_state == "paid" for inv in invoices)

                # Check if total paid matches or exceeds SO total
                total_invoiced = sum(invoices.mapped("amount_total"))
                if all_paid and total_invoiced >= so.amount_total:
                    template = self.env.ref(
                        "bora_dubai_warehouse.email_template_invoice_paid",
                        raise_if_not_found=False,
                    )
                    if template and so.warehouse_id and so.warehouse_id.email:
                        # Send ONLY to warehouse email
                        email_values = {
                            "email_to": so.warehouse_id.email
                        }
                        # ✅ Send on the SO record (so dynamic fields like warehouse info can be used)
                        template.send_mail(move.id, email_values=email_values, force_send=True)

        return res

