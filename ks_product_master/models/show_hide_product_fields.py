from odoo import models, fields


class ShowHideProductFields(models.Model):
    _inherit = 'product.template'

    part_number = fields.Char(string='Part Number', help='Unique part number for the printer', tracking=True)

    model_number = fields.Char(string='Model Number',
                                      help='Model number of the printer', tracking=True)

    accessory_group = fields.Many2one('product.accessories.group', string='Accessory group', tracking=True)

    specs_made = fields.Many2one(
        'res.country',
        string='Spec Made For',
        help='Specification made for a specific country.',
        tracking=True
    )

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        help='Country where the product is manufactured',
        tracking=True
    )

    part_code = fields.Char(
        string='Part Code / Manual Ref',
        help=(
            'Manually specify the internal reference for this product. '
            'When filled, this value is used directly as default_code for ALL '
            'variants, overriding the auto-generated structured code. '
            'Max 24 characters; uppercase alphanumeric and hyphens only.'
        ),
        tracking=True,
    )
    series_name = fields.Char(string="Series Name", tracking=True)
    ethernet = fields.Char(string="Ethernet", tracking=True)
    mouse = fields.Char(string="Mouse", tracking=True)
    keyboard = fields.Char(string="Keyboard", tracking=True)
    ports = fields.Char(string="Ports", tracking=True)
    flipkart_serial_number = fields.Char(string="Flipkart Serial Number", tracking=True)
    flipkart_listing_name = fields.Char(string="Flipkart Listing Name", tracking=True)

class AccessoriesGroup(models.Model):
    _name = 'product.accessories.group'
    _description = 'Product Accessories Group'

    name = fields.Char(required=True, string='Group Name', index=True, tracking=True)


class InkAndTonnersModelNumber(models.Model):
    _name = 'ink.tonner.model.number'
    _description = 'Ink and Tonner Model Number'

    name = fields.Char(required=True, string='Model Number', index=True, tracking=True)
