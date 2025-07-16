# -- coding: utf-8 --
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class StockMove(models.Model):
    _inherit = 'stock.move'

    show_IMEI_field = fields.Boolean(string='Show IMEI Field 1', compute='_compute_show_imei_fields')
    show_IMEI_field2 = fields.Boolean(string='Show IMEI Field 2', compute='_compute_show_imei_fields')

    def _compute_show_imei_fields(self):
        for rec in self:
            if rec.product_id.is_mobile_category_selected:
                rec.show_IMEI_field = True
                rec.show_IMEI_field2 = rec.product_id.is_dual_sim
            else:
                rec.show_IMEI_field = False
                rec.show_IMEI_field2 = False

                    


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    imei = fields.Char(string='IMEI') 
    imei2 = fields.Char(string='IMEI 2')
    # activation_date = fields.Date(string="Activation Date", help="Mobile phone activation date.")
    # activation_status = fields.Boolean(string='Is Active', help="Indicates if the mobile phone is activated or not.")
    
    
    def validate_imei(self):

        if self._context.get('active_model') != 'purchase.order':
            return 
        
        #1. Validate IMEI number
        for record in self:

            # validation for two IMEI field item
            if record.move_id.show_IMEI_field2: 
                # 1. empty imei number validation
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter IMEI numbers'))
                    
                # 2. digit and length validation, Validate IMEI format (15 digit number)
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(record.imei2) != 15:
                    if not record.lot_name:
                        raise ValidationError(_('IMEI number must be a 15-digit number.'))
                    else:
                        raise ValidationError(_('IMEI number must be a 15-digit number for Lot/Serial Number = %s.' % record.lot_name))
                    
                # 3. Uniqueness validation check 
                existing = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if existing:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                existing = self.search([('imei2', '=', record.imei2), ('id', '!=', record.id)], limit=1)
                if existing:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))

            else:
                # 1. empty imei number validation
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI numbers'))
                    
                # 2. digit and length validation, Validate IMEI format (15 digit number)
                if not record.imei.isdigit() or len(record.imei) != 15:
                    if not record.lot_name:
                        raise ValidationError(_('IMEI number must be a 15-digit number.'))
                    else:
                        raise ValidationError(_('IMEI number must be a 15-digit number for Lot/Serial Number = %s.' % record.lot_name))

                # 3. Uniqueness validation check 
                existing = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if existing:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))






class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            for line in picking.move_line_ids:
                line.validate_imei()  # your custom IMEI validator
        return super().button_validate()

