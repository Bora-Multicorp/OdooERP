from odoo import fields, models
from odoo.exceptions import UserError


class ShowBillPaymentButtonToAccountsGroup(models.Model):
    _inherit='account.move' 

    def action_post(self):
        super(ShowBillPaymentButtonToAccountsGroup, self).action_post()

        if self.env.context.get('active_model') != 'purchase.order':
            return

        sales_account_group = self.env.ref('bora_sale.account_group_for_sales')

        company_id = self.company_id.id
        accounts_users = sales_account_group.users.filtered(lambda u: u.company_id.id == company_id)

        if accounts_users:
            for user in accounts_users:

                self.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary = f'Bill {self.name} is now ready for payment.',
                    note="There is a new bill for payment.",
                    user_id=user.id,
                    date_deadline=fields.Date.context_today(self),
                )

                self.env['bus.bus']._sendone(
                    user.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'Bill {self.name} is now ready for payment.',
                        'message':  f'Activity assigned to you.',
                        'sticky': True,
                    },
                )
        else:
            raise UserError(f"No account member added for {self.company_id.name}, please contact to Administrator.")



    