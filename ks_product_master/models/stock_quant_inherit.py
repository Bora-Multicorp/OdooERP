from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

from odoo import models, fields, api, _


# For
# 1. Inventory aadjustment

class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    imei = fields.Char(string='IMEI 1', tracking=True)
    imei2 = fields.Char(string='IMEI 2', tracking=True)
    is_imei_readonly = fields.Boolean(string="IMEI Readonly", compute="_compute_is_imei_readonly")
    active_months = fields.Char(string="Activated Months", compute="_compute_active_months", store=True)
    activation_date = fields.Date(string="Activation Date", help="Mobile phone activation date.", tracking=True)
    activation_status = fields.Boolean(string='Active', help="Indicates if the mobile phone is activated or not.",
                                       tracking=True)
    origin_source = ''

    specs_made = fields.Many2one(
        'res.country',
        string='Spec Made For',
        help='Specification made for a specific country.',
        tracking=True,
    )

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        help='Country where the product is manufactured',
        tracking=True,
    )

    @api.depends_context('uid')
    def _compute_is_imei_readonly(self):
        is_sales_admin = self.env.user.has_group('sales_team.group_sale_manager')
        for rec in self:
            rec.is_imei_readonly = bool(rec.id) and not is_sales_admin


    @api.model
    def _get_inventory_fields_create(self):
        """Extend the list of fields available in inventory_mode creation."""
        # Call super to get base list and append your custom fields
        return super()._get_inventory_fields_create() + ['imei', 'imei2', 'activation_status', 'activation_date',
                                                         'active_months', 'specs_made', 'made_country']

    @api.depends('activation_date')
    def _compute_active_months(self):
        """To compute active month"""
        for rec in self:
            if rec.activation_date:
                rec.activation_status = True
                today = date.today()

                if today < rec.activation_date:
                    rec.active_months = "0"
                else:
                    delta = relativedelta(today, rec.activation_date)
                    active_months = delta.years * 12 + delta.months
                    rec.active_months = str(active_months)
            else:
                rec.activation_status = False
                rec.active_months = False  # or "" to keep it blank

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, qty=0):
        """Override to filter quants based on specs_made and made_country from context"""
        quants = super()._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, qty=qty)
        
        # Filter quants based on specs_made and made_country from context (set by stock.move)
        specs_made_id = self.env.context.get('filter_specs_made')
        made_country_id = self.env.context.get('filter_made_country')
        
        if specs_made_id or made_country_id:
            filtered_quants = self.env['stock.quant']
            for quant in quants:
                # If specs_made is specified, quant must have matching specs_made
                if specs_made_id:
                    if not quant.specs_made or quant.specs_made.id != specs_made_id:
                        continue
                # If made_country is specified, quant must have matching made_country
                if made_country_id:
                    if not quant.made_country or quant.made_country.id != made_country_id:
                        continue
                filtered_quants |= quant
            return filtered_quants
        
        return quants

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        """Override to include specs_made and made_country in inventory adjustment moves"""
        res = super()._get_inventory_move_values(qty, location_id, location_dest_id, package_id, package_dest_id)
        # Add country fields to move
        if self.specs_made:
            res['specs_made'] = self.specs_made.id
        if self.made_country:
            res['made_country'] = self.made_country.id
        # Add country fields to move line
        if res.get('move_line_ids') and len(res['move_line_ids']) > 0:
            move_line_vals = res['move_line_ids'][0][2]
            if self.specs_made:
                move_line_vals['specs_made'] = self.specs_made.id
            if self.made_country:
                move_line_vals['made_country'] = self.made_country.id
        return res

    @api.model_create_multi
    def create(self, vals_list):

        # dont remamber what this code for
        for vals in vals_list:
            lot_id = vals.get('lot_id')
            if lot_id:
                move_line = self.env['stock.move.line'].search([
                    ('lot_id', '=', lot_id)
                ], limit=1)
                if move_line:
                    vals['imei'] = move_line.imei or ''
                    vals['imei2'] = move_line.imei2 or ''
                    # Propagate country fields from move line if available
                    if move_line.specs_made:
                        vals['specs_made'] = move_line.specs_made.id
                    if move_line.made_country:
                        vals['made_country'] = move_line.made_country.id

        if self.env.context.get('inventory_mode'):
            self._check_all_validations()
        return super(StockQuantInherit, self).create(vals_list)

    def write(self, vals):
        if 'imei' in vals or 'imei2' in vals:
            if not (self.env.is_admin() or self.env.user.has_group('sales_team.group_sale_manager')):
                raise ValidationError(_('Only Sales Administrators can edit IMEI numbers on saved records.'))
        if self.env.context.get('inventory_mode'):
            self._check_all_validations()
        return super(StockQuantInherit, self).write(vals)

    def _check_all_validations(self):

        for record in self:
            is_mobile = record.product_id.product_tmpl_id.is_mobile_category_selected
            is_dual_sim = record.product_id.product_tmpl_id.is_dual_sim
            tracking = record.product_id.product_tmpl_id.tracking

            if tracking != 'none' and not record.lot_id.id:
                raise ValidationError(_('Please enter serial number.'))

            if not is_mobile:
                continue

            # Ensure IMEIs are not empty
            if is_dual_sim:
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter both IMEI numbers.'))
            else:
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI number.'))

            # Validate IMEI format (15 digit number)
            if is_dual_sim:
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(
                        record.imei2) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))
            else:
                if not record.imei.isdigit() or len(record.imei) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))

            if is_dual_sim:

                # check if brand is samsung or oneplus, as these two brands have imei1 and imei2 field's same value 
                brand_record = record.product_id.product_tmpl_id.brand_id
                brand_name = brand_record.name
                is_brand_samsung_or_oneplus = False
                if brand_name and (brand_name.lower() == 'samsung' or brand_name.lower() == 'oneplus'):
                    is_brand_samsung_or_oneplus = True

                if not is_brand_samsung_or_oneplus:
                    if record.imei == record.imei2:
                        raise ValidationError(
                            f"Both IMEI numbers must be different for product '{record.product_id.product_tmpl_id.name}'")

                imei_results = self.env['stock.quant'].search([
                    ('id', '!=', record.id),
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])
                imei2_results = self.env['stock.quant'].search([
                    ('id', '!=', record.id),
                    '|',
                    ('imei', '=', record.imei2),
                    ('imei2', '=', record.imei2)
                ])

                if len(imei_results) > 1:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                if len(imei2_results) > 1:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))

            else:
                result_items = self.env['stock.quant'].search([
                    ('id', '!=', record.id),
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])

                if len(result_items) > 0:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
