from odoo import models, fields
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'


    attachment_count = fields.Integer(
        string="Documents",
        compute="_compute_attachment_count"
    )

    def _compute_attachment_count(self):
        Attachment = self.env['ir.attachment']
        for order in self:
            order.attachment_count = Attachment.search_count([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id)
            ])


    def send_documents_in_email(self):

        if self.state != 'sale':
            raise UserError("You can only send documents for a confirmed Sales Order.")
        
        for picking in self.picking_ids:
            if picking.state not in ['done', 'cancel']:
                raise UserError("You cannot send documents while there are pending deliveries.")
            
        


        self.ensure_one()
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.id)
        ])

        attachment_ids = attachments.ids


        if not attachment_ids:
            raise UserError("No document added, you can add documents from documents section.")


        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': [self.id],
            # 'default_use_template': False, # You could use a template if you have one
            # 'default_template_id': self.env.ref('your_module.email_template_sale_order_with_docs').id, # Example template
            'default_partner_ids': [self.partner_id.id],
            'default_attachment_ids': [(6, 0, attachment_ids)],
            'default_composition_mode': 'comment',
        }

        return {
            'name': 'Send all document to customer',
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
                'default_res_model': 'sale.order',  # Explicitly set the model
                'default_res_id': self.id,
                'default_company_id': self.company_id.id,
            },
            'domain': [
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', self.id)
            ],
            'target': 'current',

            'help': ("""
                <p class="o_view_nocontent_smiling_face">
                    Attach files to sale order
                </p><p>
                    Use this feature to attach any files you would like to share with your customers<br/>
                    (e.g: airways bill, transport bill, export bill...).
                </p>
            """),
        }
    


