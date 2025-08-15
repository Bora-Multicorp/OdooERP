from odoo import fields, models, api


class ShowPaymentButtonToAccountsGroup(models.Model):
    _inherit='account.move'


    is_indian_company = fields.Boolean(
        string="Is Indian Company",
        compute='_compute_is_indian_company',
        store=True,
    )

    vessel_or_flight_no = fields.Char(string='Vessel / Flight no.')
    place_of_recipt_by_shipper = fields.Many2one('bora.sale.place.shippr', string='Place of Receipt by Shipper')
    city_and_port_of_loading = fields.Many2one('bora.city.port.loading', string='City/Port of Loading')
    city_and_port_of_discharge = fields.Many2one('bora.city.port.discharge', string='City/Port of Discharge')


    @api.depends('company_id')
    def _compute_is_indian_company(self):
        for move in self:
            if move.company_id and move.company_id.country_id.code == 'IN':
                move.is_indian_company = True
            else:
                move.is_indian_company = False



class PlaceOfReciptByShippr(models.Model):
    _name='bora.sale.place.shippr'
    _description = 'Place of Receipt by Shipper'
    _rec_name = 'place'

    place = fields.Char(string='Place', required=True)


class CityAndPortOfLoading(models.Model):
    _name='bora.city.port.loading'
    _description = 'Name of city / port of loading'
    _rec_name = 'city_port'

    city_port = fields.Char(string='City/Port of loading', required=True)


class CityAndPortOfDischarge(models.Model):
    _name='bora.city.port.discharge'
    _description='Name of city / port of discharge'
    _rec_name = 'city_port'

    city_port = fields.Char(string='city/Port of discharge', required=True)
