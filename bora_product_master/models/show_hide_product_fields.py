
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ShowHideProductFields(models.Model):
    _inherit = 'product.template'


    part_number = fields.Char(string='Part Number', help='Unique part number for the printer')

    model_number_id = fields.Many2one('ink.tonner.model.number', string='Model Number', help='Model number of the printer')

    accessory_group = fields.Many2one('product.accessories.group', string='Accessory group')

    specs_made = fields.Many2one(
        'res.country',
        string='Spec Made For',
        help='Specification made for a specific country'
    )

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        help='Country where the product is manufactured'
    )

    part_code = fields.Char(string='Part Code', help='Unique part code for the apple laptops')





class AccessoriesGroup(models.Model):
    _name = 'product.accessories.group'
    _description = 'Product Accessories Group'

    name = fields.Char(required=True, string='Group Name', index=True)



class InkAndTonnersModelNumber(models.Model):
    _name = 'ink.tonner.model.number'
    _description = 'Ink and Tonner Model Number'

    name = fields.Char(required=True, string='Model Number', index=True)


class SpecMadeFor(models.Model): 
    _name = 'spec.made.for'
    _description = 'Spec Made For'

    name = fields.Char(required=True, string='Spec (Made For)', index=True)


class MadeIn(models.Model):
    _name = 'made.in'
    _description = 'Made In'

    name = fields.Char(required=True, string='Made In', index=True)