from odoo import models, fields
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")

    sale_order_name = fields.Char('Sale Order Name')


    def action_post(self):
        super(AccountPayment, self).action_post()

        if self.env.context.get('active_model') != 'sale.order':
            return
        
        sales_account_group = self.env.ref('bora_sale.account_group_for_sales')

        company_id = self.company_id.id
        accounts_users = sales_account_group.users.filtered(lambda u: u.company_id.id == company_id)

        if accounts_users:
            for user in accounts_users:
                self.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary = f'Request fpr advance payment {self.name}, for {self.sale_order_name} generated.',
                    note="You have been assigned to receive the advance payment",
                    user_id=user.id,
                    date_deadline=fields.Date.context_today(self),
                )

                self.env['bus.bus']._sendone(
                    user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'Request fpr advance payment {self.name}, for {self.sale_order_name} generated.',
                        'message':  f'Activity assigned to you.',
                        'sticky': True,
                    },
                )
        else:
            raise UserError(f"No account member added for {self.company_id.name}, please contact to Administrator.")



class AdvancePaymentForSaleOrder(models.Model):
    _inherit = 'sale.order'

    advance_payment_count = fields.Integer(
        string="Advance Payments",
        compute="_compute_advance_payment_count"
    )

    advance_payment_total = fields.Monetary(
        string="Total Advance Payment",
        currency_field="currency_id",
        compute="_compute_advance_payments"
    )

    def _compute_advance_payments(self):
        for order in self:
            payments = self.env['account.payment'].search([
                ('sale_order_id', '=', order.id),
                # ('state', '=', 'posted'),   # only confirmed payments
            ])
            order.advance_payment_count = len(payments)
            order.advance_payment_total = sum(payments.mapped('amount'))


    def _compute_advance_payment_count(self):
        for order in self:
            order.advance_payment_count = self.env['account.payment'].search_count([
                ('sale_order_id', '=', order.id)
            ])


    def action_view_advance_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Advance Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_sale_order_id': self.id,
                'default_sale_order_name': self.name,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_currency_id': self.pricelist_id.currency_id.id,
                'force_readonly_from_fields': True,
            }
        }
