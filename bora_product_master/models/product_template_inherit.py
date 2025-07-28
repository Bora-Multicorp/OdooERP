import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    is_dual_sim = fields.Boolean(string="Is dual SIM phone", help="Check if the product is a dual SIM phone")
    
    is_mobile_category_selected = fields.Boolean(compute="_compute_category_change")
    is_packaging_material = fields.Boolean(compute="_compute_category_change")

    
    loose_or_master_carton = fields.Selection( 
        [('master_carton', 'Master Carton'), ('loose', 'Loose')],
        string="Master Carton / Loose",
        help="Specify if the product is a master carton or loose"
    )
    
    brand_id = fields.Many2one('product.brand', string="Brand", help="Brand of the product")
    
    
    model = fields.Many2one('product.model', string='Product Model', help="Select a model")
    
    # delete this line in next release
    # specs_dubai = fields.Char(string="Specs [Dubai]", help="Specifications for the Dubai market")
    # made_for_dubai = fields.Boolean(string="Made for Dubai", help="Check if the product is made for the Dubai market")    
    # made_in_india = fields.Boolean(string="Made in India", help="Check if the product is made in India")



    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=None, group_expand='_read_group_categ_id',
        required=True, help="Select the most appropriate category for this electronic device.")
    
    company_ids = fields.Many2many('res.company', string='Companies', required=True, readonly=False,
        default=lambda self: self.env.company, help="This product will appear only for users belonging to the chosen companies.")

    default_code = fields.Char('Internal Reference', compute='_compute_default_code', inverse='_set_default_code', store=True, help="Unique internal reference (SKU) for identifying the product.")




    # To change the default value of 'Track Inventory' selection field
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'By Quantity')],
        string="Tracking", required=True, default='serial', # Not having a default value here causes issues when migrating.
        compute='_compute_tracking', store=True, readonly=False, precompute=True,
        help="Ensure the traceability of a storable product in your warehouse.")    


    @api.depends('is_storable')
    def _compute_tracking(self):
        self.filtered(lambda t: not t.is_storable and t.tracking != 'none').tracking = 'none'


    attribute_ids = fields.Many2many('product.attribute')

    # To check if mobile category is selected from the Category field
    @api.depends('categ_id')
    def _compute_category_change(self):
        mobile_categ = self.env.ref('bora_product_master.product_category_type_mobile', raise_if_not_found=False)
        packaging_categ = self.env.ref('bora_product_master.product_category_type_packaging_material', raise_if_not_found=False)



        for rec in self:
            categ = rec.categ_id
            is_mobile = False
            is_packing_categ = False
            rec.attribute_ids = rec.categ_id.product_attributes.ids

            while categ and (not is_mobile or not is_packing_categ):
                if categ == mobile_categ:
                    is_mobile = True
                if categ == packaging_categ:
                    is_packing_categ = True
                categ = categ.parent_id

            rec.is_mobile_category_selected = is_mobile
            rec.is_packaging_material = is_packing_categ

        





    # To generate SKU
    def _generate_and_assign_sku(self):
        self.ensure_one()


        variants = self.env['product.product'].with_context(active_test=False).search([('product_tmpl_id', '=', self.id)])
        if variants:
            for variant in variants:
                variant.default_code = self._generate_sku(variant.id)
        else:
            self.default_code = self._generate_sku(self.id)
    
    
    def _generate_sku(self, varient_id):
        self.ensure_one()

        # Prefix
        if self.loose_or_master_carton == 'master_carton':
            prefix = 'MC'
        elif self.loose_or_master_carton == 'loose':
            prefix = 'L'
        else:
            prefix = 'GEN'

        # Name
        name_part = (self.name or "").upper().replace(" ", "")

        # Attributes
        attr_part = ""
        variants = self.env['product.product'].with_context(active_test=False).search([('product_tmpl_id', '=', self.id)])
        for variant in variants:
            if variant.id == varient_id:
                values = variant.product_template_attribute_value_ids.mapped('name')
                if values:
                    attr_part = "-".join(val.upper().replace(" ", "") for val in sorted(values))

        sku = f"{prefix}-{name_part}"
        if attr_part:
            sku += f"-{attr_part}-{varient_id}"
        else:
            sku += f"-{self.id}"

        return sku




    # To set the product name in ALL CAPS based on model number
    @api.onchange('model')
    def _onchange_model(self):
        if self.model:
            self.name = self.model.name.upper()

    def action_update_quantity_on_hand(self):
        
        # check IMEI field visibility based on product category and dual SIM status
        show_IMEI_field = False
        show_IMEI_field2 = False
        for rec in self:
            if rec.is_mobile_category_selected:
                if rec.is_dual_sim:
                    show_IMEI_field = True
                    show_IMEI_field2 = True
                else:
                    show_IMEI_field = True

        # update the action context to include IMEI fields visibility
        self.ensure_one()
        action = super().action_update_quantity_on_hand()

        if isinstance(action, dict):
            action['context'] = dict(action.get('context', {}), show_IMEI= show_IMEI_field, show_IMEI2 = show_IMEI_field2)

        return action


    @api.model_create_multi
    def create(self, vals_list):


        # if packaging item then set is_storable and tracking to False, as if this enables then it requires serial number
        for vals in vals_list:
            categ_id = vals.get('categ_id')
            packaging_categ = self.env.ref('bora_product_master.product_category_type_packaging_material', raise_if_not_found=False)
            if categ_id == packaging_categ.id:
                vals['tracking'] = 'none'


        # 1. Capitalize product name in each dict
        for vals in vals_list:
            if vals.get('name'):
                vals['name'] = vals['name'].upper()

        # 2. Create records
        records = super().create(vals_list)

        # 3. Generate SKUs
        for rec in records:
            rec._generate_and_assign_sku()

        return records



    def write(self, vals):

        # if packaging item then set is_storable and tracking to False, as if this enables then it requires serial number
        categ_id = vals.get('categ_id')
        packaging_categ = self.env.ref('bora_product_master.product_category_type_packaging_material', raise_if_not_found=False)
        if categ_id == packaging_categ.id:
            vals['tracking'] = 'none'

        # 1. capitalize product name
        if vals.get('name'):
            vals['name'] = vals['name'].upper()

        res = super().write(vals)

        # 2. Trigger SKU generation if relevant fields are updated
        if any(field in vals for field in ['name', 'attribute_line_ids', 'loose_or_master_carton']):
            for rec in self:
                rec._generate_and_assign_sku()

        return res

class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char(string="Brand Name", required=True)
    
    
class ProductModel(models.Model):
    _name = 'product.model'
    _description = 'Product Model'
    
    name = fields.Char(string='Product Model', required=True, index=True)