from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warehouse_warning = fields.Html(
        compute="_compute_warehouse_warning",
        sanitize=False,
    )

    @api.depends("warehouse_id")
    def _compute_warehouse_warning(self):
        for order in self:
            if not order.warehouse_id:
                order.warehouse_warning = (
                    '<div class="alert alert-warning" role="alert">'
                    '⚠️ <strong>%s</strong>'
                    "</div>" % _("There is no warehouse on this Sales Order. Please add a warehouse.")
                )
            else:
                order.warehouse_warning = False

    trade_type = fields.Selection([
        ('local', 'Local Trade'),
        ('freezone', 'Freezone Trade'),
        ('bora_global', 'Bora Global'),
    ], default='freezone', string='Trade Type')


    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.trade_type in ['freezone', 'bora_global']:
                order._send_wh_responsible_email()
        return res

    def _send_wh_responsible_email(self):
        self.ensure_one()
        warehouse = self.warehouse_id
        if not warehouse:
            return

        # Collect responsible person emails from the warehouse.
        recipients = [p.email for p in warehouse.responsible_person_ids if p.email]

        # Add the warehouse's own email if it exists.
        if warehouse.email:
            recipients.append(warehouse.email)

        if recipients:
            template = self.env.ref('bora_dubai_warehouse.email_template_wh_notification')

            # Use email_values to dynamically set the recipient list.
            email_values = {
                'email_to': ','.join(recipients),
            }
            template.send_mail(self.id, force_send=True, email_values=email_values)
