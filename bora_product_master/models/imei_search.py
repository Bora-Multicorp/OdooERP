from odoo import models, fields, api

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    imei_search = fields.Char("IMEI Search", compute="_compute_imei_search", store=True, index=True)

    @api.depends('move_line_ids.imei', 'move_line_ids.imei2', 'move_line_ids.lot_id')
    def _compute_imei_search(self):
        for picking in self:
            imeis = set()

            # From stock.move.line
            imeis.update(filter(None, picking.move_line_ids.mapped('imei')))
            imeis.update(filter(None, picking.move_line_ids.mapped('imei2')))

            # From stock.quant via lot_id
            lot_ids = picking.move_line_ids.mapped('lot_id').ids
            if lot_ids:
                quants = self.env['stock.quant'].search([('lot_id', 'in', lot_ids)])
                imeis.update(filter(None, quants.mapped('imei')))
                imeis.update(filter(None, quants.mapped('imei2')))

            picking.imei_search = ','.join(imeis)





class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    imei_search = fields.Char("IMEI Search", compute="_compute_imei_search", store=True, index=True)

    @api.depends('imei', 'imei2', 'lot_id', 'product_id', 'location_id') # Dependencies updated
    def _compute_imei_search(self):
        for quant in self:
            imeis = set()

            # Access IMEI fields directly from the quant record
            if quant.imei:
                imeis.add(quant.imei)
            if quant.imei2:
                imeis.add(quant.imei2)

            quant.imei_search = ','.join(filter(None, imeis))