# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ecom_id = fields.Many2one(
        'bora.ecom.master',
        string='Purpose',
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

    def _get_ecom_picking_type(self, company_id=None):
        """Find the incoming picking type of the first E-Commerce warehouse."""
        comp_id = (company_id.id if hasattr(company_id, 'id') else company_id) or self.company_id.id or self.env.company.id
        ecom_wh = self.env['stock.warehouse'].search([
            ('is_ecommerce_warehouse', '=', True),
            ('company_id', '=', comp_id),
        ], limit=1)
        if not ecom_wh:
            ecom_wh = self.env['stock.warehouse'].search([
                ('is_ecommerce_warehouse', '=', True),
                '|', ('company_id', '=', comp_id), ('company_id', '=', False),
            ], limit=1)
        if ecom_wh:
            picking_type = ecom_wh.in_type_id or self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', ecom_wh.id),
            ], limit=1)
            if picking_type:
                return picking_type
        return False

    def _get_standard_picking_type(self, company_id=None):
        """Find the standard incoming picking type (non-ecommerce or default)."""
        comp_id = (company_id.id if hasattr(company_id, 'id') else company_id) or self.company_id.id or self.env.company.id
        std_wh = self.env['stock.warehouse'].search([
            ('is_ecommerce_warehouse', '=', False),
            ('company_id', '=', comp_id),
        ], limit=1)
        if std_wh and std_wh.in_type_id:
            return std_wh.in_type_id
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', comp_id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', False),
            ], limit=1)
        return picking_type[:1] if picking_type else False

    @api.onchange('ecom_id')
    def _onchange_ecom_id(self):
        """
        When Purpose (E-Com category) changes:
        - If E-Commerce is selected:
          - Show marketplace_id.
          - Reflect E-Commerce warehouse into Deliver To (picking_type_id).
        - If NOT E-Commerce (Domestic, Export, or empty):
          - Clear marketplace_id and keep it hidden.
          - If Deliver To was currently pointing to an E-Commerce warehouse,
            revert it back to the standard warehouse.
        """
        is_ecom = False
        if self.ecom_id:
            if self.ecom_id.is_ecommerce:
                is_ecom = True
            elif (self.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com'):
                is_ecom = True
        self.is_ecom_po = is_ecom

        if is_ecom:
            ecom_picking_type = self._get_ecom_picking_type(self.company_id)
            if ecom_picking_type:
                self.picking_type_id = ecom_picking_type
        else:
            self.marketplace_id = False
            if self.picking_type_id and self.picking_type_id.warehouse_id.is_ecommerce_warehouse:
                std_picking_type = self._get_standard_picking_type(self.company_id)
                if std_picking_type:
                    self.picking_type_id = std_picking_type

    @api.model
    def _default_picking_type(self):
        default_ecom_id = self.env.context.get('default_ecom_id')
        if default_ecom_id:
            ecom = self.env['bora.ecom.master'].browse(default_ecom_id)
            if ecom.exists() and (ecom.is_ecommerce or (ecom.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com')):
                company_id = self.env.context.get('company_id') or self.env.company.id
                ecom_pt = self._get_ecom_picking_type(company_id)
                if ecom_pt:
                    return ecom_pt
        return super()._default_picking_type()

    def _get_picking_type(self, company_id):
        if hasattr(self, 'ecom_id') and self.ecom_id and (self.ecom_id.is_ecommerce or (self.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com')):
            ecom_pt = self._get_ecom_picking_type(company_id)
            if ecom_pt:
                return ecom_pt
        return super()._get_picking_type(company_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'ecom_id' in vals and not vals.get('ecom_id'):
                vals['marketplace_id'] = False

            # If ecom_id is provided and represents E-Commerce, set e-commerce warehouse if not manually chosen
            ecom_id = vals.get('ecom_id')
            is_ecom = False
            if ecom_id:
                ecom = self.env['bora.ecom.master'].browse(ecom_id)
                if ecom.exists() and (ecom.is_ecommerce or (ecom.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com')):
                    is_ecom = True

            if is_ecom and not vals.get('picking_type_id'):
                company_id = vals.get('company_id') or self.env.context.get('company_id') or self.env.company.id
                ecom_picking_type = self._get_ecom_picking_type(company_id)
                if ecom_picking_type:
                    vals['picking_type_id'] = ecom_picking_type.id

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

    def _prepare_picking(self):
        vals = super()._prepare_picking()
        if self.ecom_id and (self.ecom_id.is_ecommerce or (self.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com')):
            vals['ecom_id'] = self.ecom_id.id
            if self.marketplace_id:
                vals['marketplace_id'] = self.marketplace_id.id
        return vals

    def _create_picking(self):
        res = super()._create_picking()
        for order in self:
            if order.ecom_id and (order.ecom_id.is_ecommerce or (order.ecom_id.name or '').strip().lower() in ('e-commerce', 'ecommerce', 'e-com')):
                pickings = order.picking_ids.filtered(lambda p: not p.ecom_id)
                if pickings:
                    vals_to_write = {'ecom_id': order.ecom_id.id}
                    if order.marketplace_id:
                        vals_to_write['marketplace_id'] = order.marketplace_id.id
                    pickings.write(vals_to_write)
        return res
