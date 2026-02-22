from datetime import timedelta
from odoo import models, api


class ProcurementSlaCron(models.Model):
    _name = 'procurement.sla.cron'
    _description = 'Procurement SLA Breach Checker'

    @api.model
    def cron_check_sla_breach(self):
        breached_pos = self.env['purchase.order']

        pickings = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'incoming'),
            ('state', '=', 'done'),
            ('purchase_id', '!=', False),
        ])

        for picking in pickings:
            po = picking.purchase_id
            if not po:
                continue
            vendor = po.partner_id

            # Skip if already breached or missing config
            if po.sla_status == 'breached':
                continue

            if not vendor.sla_lead_time_days or not po.date_approve:
                continue

            expected_date = po.date_approve + timedelta(
                days=vendor.sla_lead_time_days
            )

            if picking.date_done and picking.date_done > expected_date:
                po.sla_status = 'breached'
                breached_pos |= po

        # Send email if any breach found
        if breached_pos:
            self._send_sla_breach_email(breached_pos)

    def _send_sla_breach_email(self, breached_pos):
        template = self.env.ref(
            'vendor_sla_management.email_template_sla_breach',
            raise_if_not_found=False
        )
        if not template:
            return

        procurement_group = self.env.ref('purchase.group_purchase_manager')
        users = procurement_group.users.filtered(lambda u: u.email)

        emails = ','.join(users.mapped('email'))

        template.with_context(
            breached_pos=breached_pos
        ).send_mail(
            breached_pos[0].id,
            email_values={'email_to': emails},
            force_send=True
        )


