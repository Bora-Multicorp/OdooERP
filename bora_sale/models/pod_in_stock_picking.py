from odoo import fields, models
from odoo.exceptions import UserError


class POD_in_stock_picking(models.Model):
    _inherit = 'stock.picking'

    attachment_count = fields.Integer(
        string="Proof of delivery",
        compute="_compute_attachment_count"
    )

    is_pod_needed = fields.Boolean(
        compute="_compute_is_pod_needed",
        store=False
    )

    def _compute_is_pod_needed(self):
        for rec in self:
            if rec.sale_id.payment_term_id.name:
                # rec.is_pod_needed = rec.picking_type_code == 'outgoing' and rec.state == 'done' and rec.sale_id.payment_term_id.name.lower() == 'cash' and (rec.company_id.company_registry == '1804237.01' or rec.company_id.company_registry == '3892')
                rec.is_pod_needed = rec.state == 'done' and rec.sale_id.payment_term_id.name.lower() == 'cash' and (rec.company_id.company_registry == '1804237.01' or rec.company_id.company_registry == '3892')
            else:
                rec.is_pod_needed = False


    def _compute_attachment_count(self):
        Attachment = self.env['ir.attachment']
        for order in self:
            order.attachment_count = Attachment.search_count([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', order.id)
            ])


    def send_pod_to_accounts_group(self):
        self.ensure_one()
        sales_account_group = self.env.ref('bora_sale.account_group_for_sales')
        sales_account_group_partner_ids = sales_account_group.users.mapped('partner_id').ids

        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', self.id)
        ])

        attachment_ids = attachments.ids

        if not attachment_ids:
            raise UserError("No document added, you can add documents from documents section.")
        
        if not sales_account_group.users:
            raise UserError("No account member added, please contact to Administrator.")
        

        ctx = {
            'default_model': 'stock.picking',
            'default_res_ids': [self.id],
            # 'default_use_template': False, # You could use a template if you have one
            # 'default_template_id': self.env.ref('your_module.email_template_sale_order_with_docs').id, # Example template
            'default_partner_ids': sales_account_group_partner_ids,
            'default_attachment_ids': [(6, 0, attachment_ids)],
            'default_composition_mode': 'comment',
            'default_subject': 'Proof of Delivery for ' + self.name,
            'default_body': '<p>Dear Team,</p><p>Please find the Proof of Delivery for <b>' + self.name + '</b> attached to this email.</p><p>Regards,<br/>Your Team</p>'
        }

        return {
            'name': 'Send POD to accounts group',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'view_id': self.env.ref('mail.email_compose_message_wizard_form').id,
            'target': 'new',
            'context': ctx,
        }


    def action_view_attachments(self):
        self.ensure_one()
        return {
            'name': ('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'context': {
                'default_res_model': 'stock.picking',  # Explicitly set the model
                'default_res_id': self.id,
                'default_company_id': self.company_id.id,
            },
            'domain': [
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', self.id)
            ],
            'target': 'current',

            'help': ("""
                <p class="o_view_nocontent_smiling_face">
                    Attach POD(proof of delivery)
                </p><p>
                    Use this feature to attach POD you would like to share with accounts group.<br/>
                </p>
            """),
        }
