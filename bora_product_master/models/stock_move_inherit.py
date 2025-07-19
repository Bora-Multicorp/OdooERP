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

        # some time it shows None
        # if self._context.get('active_model') != 'purchase.order':
        #     return 

         
        #1. Validate IMEI number and Serial number
        for record in self:

            #1. Ensure IMEIs are not empty
            if record.move_id.show_IMEI_field2:
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter both IMEI numbers.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI number 1.'))
                
            
            #2. Validate IMEI format (15 digit number)
            if record.move_id.show_IMEI_field2:
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(record.imei2) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei.isdigit() or len(record.imei) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))




            # 3.1 Uniqueness of IMEI check in same lines
            if record.move_id.show_IMEI_field2:
                exist = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                exist = self.search([('imei2', '=', record.imei2), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))
            elif record.move_id.show_IMEI_field:
                exist = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))



            # 3.2 Uniqueness of IMEI check in all other saved items
            if record.move_id.show_IMEI_field2:

                if record.imei == record.imei2:
                    raise ValidationError(_('Both IMEI numbers must be different'))
                
                imei_results = self.env['stock.quant'].search([
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])
                imei2_results = self.env['stock.quant'].search([
                    '|',
                    ('imei', '=', record.imei2),
                    ('imei2', '=', record.imei2)
                ])

                if len(imei_results) > 1:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                if len(imei2_results) > 1:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))

            elif record.move_id.show_IMEI_field:
                result_items = self.env['stock.quant'].search([
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])

                if len(result_items) > 1:
                    raise ValidationError(_('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))


            # 4.1 Uniqueness of Serial number check in same lines
            exist = self.search([('lot_name', '=',  record.lot_name), ('id', '!=', record.id)], limit=1)
            if exist:
                raise ValidationError(_('Serial number must be unique, the serial number(%s) is already used in another stock item.' % record.lot_name))
            
            #4.2 Uniqueness of Serial number check in all other saved items
            results = self.env['stock.quant'].search([
                ('lot_id.name', '=', record.lot_name)
            ])

            if len(results) > 0:
                raise ValidationError(_('Serial number must be unique, the Serial number(%s) is already used in another stock item.' % record.lot_name))











class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            for line in picking.move_line_ids:
                line.validate_imei()  # custom validator
        return super().button_validate()

