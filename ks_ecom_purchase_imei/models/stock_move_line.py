# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    imei_status = fields.Selection([
        ('not_applicable', 'Not Applicable'),
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string="IMEI Status",
        default='not_applicable',
        index=True,
        help="Status of IMEI validation: Pending (awaiting validation), Pass (validated successfully), Fail (validation failed)")

    @api.model
    def create(self, vals_list):
        # Support multiple record creation
        records = super().create(vals_list)

        mobile_category = self.env.ref(
            'ks_product_master.product_category_type_mobile',
            raise_if_not_found=False
        )

        if mobile_category:
            for line in records:
                product = line.product_id
                if product and product.categ_id == mobile_category:
                    # Set your custom field here
                    line.imei_status = 'pending'  # OR any field you want to update
                    # Example:
                    # line.is_qc_pending = True
                    # line.state = 'pending'
        return records

    show_imei_fields = fields.Boolean(
        string="Show IMEI Fields",
        compute='_compute_show_imei_fields',
        help="Determines if IMEI fields should be shown based on product category.",
    )
    
    is_dual_sim = fields.Boolean(
        string="Is Dual SIM",
        compute='_compute_show_imei_fields',
        help="Determines if the product requires two IMEI numbers.",
    )
    
    is_imei_validated = fields.Boolean(
        string="IMEI Validated",
        default=False,
        help="Indicates if IMEI has been successfully validated against manifest.",
    )
    
    is_imei_mismatch = fields.Boolean(
        string="IMEI Mismatch",
        default=True,
        index=True,
        help="Indicates when an IMEI validation mismatch has occurred. "
             "Lines with mismatch will be moved to On Hold location and blocked from stock.",
    )
    
    original_location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string="Original Destination",
        help="Original destination location before being moved to On Hold.",
    )

    @api.depends('product_id', 'product_id.categ_id')
    def _compute_show_imei_fields(self):
        """
        Determine if IMEI fields should be shown based on product category.
        Uses is_mobile_category_selected and is_dual_sim from product template
        if ks_product_master module is installed, otherwise checks category name.
        """
        for line in self:
            show_imei = False
            is_dual = False
            
            if line.product_id:
                product_tmpl = line.product_id.product_tmpl_id
                
                # Check if ks_product_master fields exist
                if hasattr(product_tmpl, 'is_mobile_category_selected'):
                    show_imei = product_tmpl.is_mobile_category_selected
                    if hasattr(product_tmpl, 'is_dual_sim'):
                        is_dual = product_tmpl.is_dual_sim
                else:
                    # Fallback: check if category name contains 'mobile' or 'phone'
                    mobile_categ = self.env.ref('ks_product_master.product_category_type_mobile',
                                                raise_if_not_found=False)

                    categ = line.product_id.categ_id
                    while categ:
                        if categ == mobile_categ:
                            is_mobile = True
                            break
                        categ = categ.parent_id
            
            line.show_imei_fields = show_imei
            line.is_dual_sim = is_dual

    @api.onchange('imei')
    def _onchange_imei(self):
        """Validate IMEI format on change."""
        if self.imei and self.show_imei_fields:
            imei_clean = self.imei.strip()
            if imei_clean and (not imei_clean.isdigit() or len(imei_clean) != 15):
                return {
                    'warning': {
                        'title': _('Invalid IMEI'),
                        'message': _('IMEI should be a 15-digit number.'),
                    }
                }

    @api.onchange('imei2')
    def _onchange_imei2(self):
        """Validate IMEI2 format on change."""
        if self.imei2 and self.is_dual_sim:
            imei2_clean = self.imei2.strip()
            if imei2_clean and (not imei2_clean.isdigit() or len(imei2_clean) != 15):
                return {
                    'warning': {
                        'title': _('Invalid IMEI 2'),
                        'message': _('IMEI 2 should be a 15-digit number.'),
                    }
                }

    def _get_imei_on_hold_location(self):
        """Get the configured On Hold location or default."""
        # First check system parameter
        ICPSudo = self.env['ir.config_parameter'].sudo()
        location_id = ICPSudo.get_param('ks_ecom_purchase_imei.imei_on_hold_location_id', default=False)
        
        if location_id:
            try:
                location = self.env['stock.location'].browse(int(location_id))
                if location.exists():
                    return location
            except (ValueError, TypeError):
                pass
        
        # Fallback to default XML location
        default_location = self.env.ref('ks_ecom_purchase_imei.imei_on_hold_location', raise_if_not_found=False)
        if default_location:
            return default_location
        
        # Last resort - return None, don't change location
        return None

    def action_set_imei_mismatch(self, mismatch_reason=''):
        """
        Set IMEI mismatch flag and move line to On Hold location.
        Called when IMEI validation fails.
        """
        on_hold_location = self._get_imei_on_hold_location()
        
        for line in self:
            if line.is_imei_mismatch:
                # Store original destination before moving to On Hold
                line.original_location_dest_id = line.location_dest_id
                
                # # Set mismatch flag
                # line.is_imei_mismatch = True
                
                # Move to On Hold location if available
                if on_hold_location and line.location_dest_id != on_hold_location:
                    line.location_dest_id = on_hold_location
        
        return True

    def action_resolve_imei_mismatch(self):
        """
        Resolve IMEI mismatch - clear flag and restore original destination.
        Called via button in form view.
        """
        for line in self:
            if line.is_imei_mismatch:
                line.is_imei_mismatch = False
                line.is_imei_validated = True
                
                # Restore original destination if available
                if line.original_location_dest_id:
                    line.location_dest_id = line.original_location_dest_id
                    line.original_location_dest_id = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('IMEI mismatch resolved. Line can now be processed normally.'),
                'type': 'success',
                'sticky': False,
            }
        }
