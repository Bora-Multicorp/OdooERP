# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ecom_id = fields.Many2one(
        'bora.ecom.master',
        string='E-Com',
        tracking=True,
        copy=True,
        ondelete='restrict',
        help="Business category applicable to this Purchase Order (e.g., Domestic, E-Commerce, Export).",
    )
    marketplace_id = fields.Many2one(
        'bora.marketplace.master',
        string='Marketplace',
        tracking=True,
        copy=True,
        ondelete='restrict',
        help="Applicable marketplace for E-Commerce transactions (e.g., Amazon, Flipkart).",
    )
    is_ecom_po = fields.Boolean(
        string='Is E-Commerce PO',
        compute='_compute_is_ecom_po',
        store=True,
        index=True,
        help="Technical flag indicating if this Purchase Order is identified as an E-Commerce PO.",
    )

    @api.depends('ecom_id', 'ecom_id.name', 'ecom_id.is_ecommerce')
    def _compute_is_ecom_po(self):
        for order in self:
            is_ecom = False
            if order.ecom_id:
                if order.ecom_id.is_ecommerce:
                    is_ecom = True
                elif (order.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com'):
                    is_ecom = True
            order.is_ecom_po = is_ecom

    @api.onchange('ecom_id')
    def _onchange_ecom_id(self):
        """
        When E-Com category changes:
        - Update is_ecom_po immediately for view responsiveness.
        - When the user changes from E-Commerce to Domestic, Export, or empty,
          clear marketplace_id and keep it hidden.
        """
        is_ecom = False
        if self.ecom_id:
            if self.ecom_id.is_ecommerce:
                is_ecom = True
            elif (self.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com'):
                is_ecom = True
        self.is_ecom_po = is_ecom
        if not is_ecom:
            self.marketplace_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'ecom_id' in vals and not vals.get('ecom_id'):
                vals['marketplace_id'] = False
        return super().create(vals_list)

    def write(self, vals):
        if 'ecom_id' in vals and 'marketplace_id' not in vals:
            ecom = self.env['bora.ecom.master'].browse(vals['ecom_id']) if vals['ecom_id'] else False
            is_ecom = False
            if ecom:
                if ecom.is_ecommerce or (ecom.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com'):
                    is_ecom = True
            if not is_ecom:
                vals['marketplace_id'] = False
        return super().write(vals)
