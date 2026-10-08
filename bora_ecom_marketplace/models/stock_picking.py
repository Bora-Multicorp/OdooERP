# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ecom_id = fields.Many2one(
        'bora.ecom.master',
        string='Purpose',
        compute='_compute_ecom_data',
        store=True,
        readonly=True,
        precompute=True,
        copy=False,
        tracking=True,
        ondelete='restrict',
        help="Business category applicable to this transfer/receipt (set from related purchase order).",
    )
    marketplace_id = fields.Many2one(
        'bora.marketplace.master',
        string='Marketplace',
        compute='_compute_ecom_data',
        store=True,
        readonly=True,
        precompute=True,
        copy=False,
        tracking=True,
        ondelete='restrict',
        help="Applicable marketplace for E-Commerce transactions.",
    )
    is_ecom_picking = fields.Boolean(
        string='Is E-Commerce Picking',
        compute='_compute_is_ecom_picking',
        store=True,
        index=True,
        help="Technical flag indicating if this transfer is identified as E-Commerce.",
    )

    @api.depends('ecom_id', 'ecom_id.name', 'ecom_id.is_ecommerce')
    def _compute_is_ecom_picking(self):
        for picking in self:
            is_ecom = False
            if picking.ecom_id:
                if picking.ecom_id.is_ecommerce:
                    is_ecom = True
                elif (picking.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com'):
                    is_ecom = True
            picking.is_ecom_picking = is_ecom

    @api.depends('purchase_id', 'purchase_id.ecom_id', 'purchase_id.ecom_id.is_ecommerce', 'purchase_id.marketplace_id')
    def _compute_ecom_data(self):
        for picking in self:
            po = picking.purchase_id
            if po and po.ecom_id and (po.ecom_id.is_ecommerce or (po.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com')):
                picking.ecom_id = po.ecom_id
                picking.marketplace_id = po.marketplace_id if po.marketplace_id else False
            elif not picking.ecom_id:
                picking.ecom_id = False
                picking.marketplace_id = False
