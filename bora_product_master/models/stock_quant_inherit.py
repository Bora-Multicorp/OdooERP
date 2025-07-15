from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta



class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    imei = fields.Char(string='IMEI')
    imei2 = fields.Char(string='IMEI 2')
    activation_date = fields.Date(string="Activation Date", help="Mobile phone activation date.")
    remaining_months = fields.Char(string="Remaining Months", compute="_compute_remaining_months", store=True)
    activation_status = fields.Boolean(string='Active', help="Indicates if the mobile phone is activated or not.")

        
    @api.model
    def _get_inventory_fields_create(self):
        """Extend the list of fields available in inventory_mode creation."""
        # Call super to get base list and append your custom fields
        return super()._get_inventory_fields_create() + ['imei', 'imei2', 'activation_status','activation_date','remaining_months']


    @api.depends('activation_date')
    def _compute_remaining_months(self):
        
        for rec in self:
            if rec.activation_date:
                rec.activation_status = True
                today = date.today()

                if today < rec.activation_date:
                    rec.remaining_months = "30"
                else:
                    delta = relativedelta(today, rec.activation_date)
                    used_months = delta.years * 12 + delta.months
                    remaining = max(0, 30 - used_months)
                    rec.remaining_months = str(remaining)
            else:
                rec.activation_status = False
                rec.remaining_months = False  # or "" to keep it blank


    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            move_line = self.env['stock.move.line'].search([
                ('lot_id', '=', vals.get('lot_id'))
            ], limit=1)
            if move_line:
                if move_line.imei:
                    vals['imei'] = move_line.imei
                if move_line.imei2:
                    vals['imei2'] = move_line.imei2

        self._check_all_validations()

        records = super(StockQuantInherit, self).create(vals_list)

        return records
    

    def write(self, vals):
        self._check_all_validations()
        return super(StockQuantInherit, self).write(vals)


    def _check_all_validations(self):


        if self._context.get('active_model') != 'product.template':
            return 

        for record in self:

            #Ensure IMEI1 is not empty
            if not record.imei or not record.imei2:
                raise ValidationError(_('Please enter IMEI number.'))

            #Validate IMEI format (15 digit number)
            if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(record.imei2) != 15:
                raise ValidationError(_('IMEI number must be a 15-digit number.'))

            #Uniqueness check (you may adjust based on your model)
            existing = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
            if existing:
                raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
            
            existing = self.search([('imei2', '=', record.imei2), ('id', '!=', record.id)], limit=1)
            if existing:
                raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))