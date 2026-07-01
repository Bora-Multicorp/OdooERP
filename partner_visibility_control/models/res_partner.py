# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.query import Query


class ResPartner(models.Model):
    """Extend res.partner with multi-user assignment fields and a context-
    aware search filter.

    Filtering is split across two layers:

    Layer 1 — view domain attributes (sale_order_views.xml / purchase_order_views.xml):
      Enforce static business rules (customer_rank, KYC gate, is_approved).
      These ONLY affect the dropdown; they never block reads of already-
      selected records, so they cannot cause access errors on existing orders.

    Layer 2 — this _search override:
      Enforces user-scoped assignment (salesperson_ids / purchase_executive_ids)
      for non-admin users.  Admin users bypass Layer 2 entirely.
    """

    _inherit = 'res.partner'

    # Users responsible for this contact on the Sales side.
    salesperson_ids = fields.Many2many(
        comodel_name='res.users',
        relation='res_partner_salesperson_rel',
        column1='partner_id',
        column2='user_id',
        string='Sales Executives',
        help=(
            'Users who can select this contact as the customer in a '
            'Sales Order.  Leave empty to make the contact invisible '
            'in all Sales Order partner dropdowns (except for admins).'
        ),
    )

    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='partner_id',
        string='Purchase Orders',
    )

    # Users responsible for this contact on the Purchase side.
    purchase_executive_ids = fields.Many2many(
        comodel_name='res.users',
        relation='res_partner_purchase_executive_rel',
        column1='partner_id',
        column2='user_id',
        string='Purchase Executives',
        help=(
            'Users who can select this contact as the vendor in a '
            'Purchase Order.  Leave empty to make the contact invisible '
            'in all Purchase Order partner dropdowns (except for admins).'
        ),
    )

    # ------------------------------------------------------------------ #
    # User-scoped search filter (Layer 2)                                  #
    # ------------------------------------------------------------------ #

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None) -> 'Query':
        ctx = self.env.context

        if not self.env.is_admin():
            if ctx.get('filter_by_salesperson'):
                domain = expression.AND([
                    domain,
                    [('salesperson_ids', 'in', [self.env.uid])],
                ])
            elif ctx.get('filter_by_purchase_executive'):
                domain = expression.AND([
                    domain,
                    [('purchase_executive_ids', 'in', [self.env.uid])],
                ])
            elif ctx.get('restrict_by_sales_executive'):
                # Hard filter for Contacts list view: only assigned contacts
                domain = expression.AND([
                    domain,
                    ['|',
                        ('user_ids', '!=', False),
                        '|',
                        ('salesperson_ids', 'in', [self.env.uid]),
                        ('purchase_executive_ids', 'in', [self.env.uid]),
                    ],
                ])

        return super()._search(domain, offset=offset, limit=limit, order=order)
