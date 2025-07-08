from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    imei = fields.Char(string='IMEI')
    imei2 = fields.Char(string='IMEI 2')
    activation_status = fields.Boolean(string='Active', help="Indicates if the mobile phone is activated or not.")

        
    @api.model
    def _get_inventory_fields_create(self):
        """Extend the list of fields available in inventory_mode creation."""
        # Call super to get base list and append your custom fields
        return super()._get_inventory_fields_create() + ['imei', 'imei2', 'activation_status']


    @api.model_create_multi
    def create(self, vals_list):
        records = super(StockQuantInherit, self).create(vals_list)
        records._check_all_validations()
        return records

    # @api.model
    # def create(self, vals):
    #     self._check_all_validations()
    #     return super(StockQuantInherit, self).create(vals)

    def write(self, vals):
        self._check_all_validations()
        return super(StockQuantInherit, self).write(vals)


    def _check_all_validations(self):
        for record in self:

            # Validate lot_id (required if you want it to be mandatory)
            if not record.lot_id:
                raise ValidationError(_('You need to supply a Lot/Serial number for products %s.', record.product_id.name))

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
