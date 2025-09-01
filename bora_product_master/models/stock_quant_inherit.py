from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


# For
# 1. Inventory aadjustment

class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    imei = fields.Char(string='IMEI')
    imei2 = fields.Char(string='IMEI 2')
    active_months = fields.Char(string="Activated Months", compute="_compute_active_months", store=True)
    activation_date = fields.Date(string="Activation Date", help="Mobile phone activation date.")
    activation_status = fields.Boolean(string='Active', help="Indicates if the mobile phone is activated or not.")
    origin_source = ''
        

        
    @api.model
    def _get_inventory_fields_create(self):
        """Extend the list of fields available in inventory_mode creation."""
        # Call super to get base list and append your custom fields
        return super()._get_inventory_fields_create() + ['imei', 'imei2', 'activation_status','activation_date','active_months']

    @api.depends('activation_date')
    def _compute_active_months(self):
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

        if self.env.context.get('inventory_mode'):
            self._check_all_validations()
        return super(StockQuantInherit, self).create(vals_list)



    def write(self, vals):
        if self.env.context.get('inventory_mode'):
            self._check_all_validations()  
        return super(StockQuantInherit, self).write(vals)



    def _check_all_validations(self):

        for record in self:
            is_mobile = record.product_id.product_tmpl_id.is_mobile_category_selected
            is_dual_sim = record.product_id.product_tmpl_id.is_dual_sim

            if not record.lot_id.id:
                raise ValidationError(_('Please enter serial number.'))
            
            if not is_mobile:
                continue

            #Ensure IMEIs are not empty
            if is_dual_sim:
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter both IMEI numbers.'))
            else:
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI number.'))


            #Validate IMEI format (15 digit number)
            if is_dual_sim:
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(record.imei2) != 15:
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
                        raise ValidationError(_('Both IMEI numbers must be different'))
                    
                
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
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                if len(imei2_results) > 1:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))

            else:
                result_items = self.env['stock.quant'].search([
                    ('id', '!=', record.id),
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])

                if len(result_items) > 0:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))

