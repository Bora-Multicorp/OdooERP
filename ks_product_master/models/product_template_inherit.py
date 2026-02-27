from odoo import models, fields, api


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    is_dual_sim = fields.Boolean(string="Is dual SIM phone", help="Check if the product is a dual SIM phone",
                                 tracking=True,default=True)

    is_mobile_category_selected = fields.Boolean(compute="_compute_category_change", tracking=True)
    is_packaging_material = fields.Boolean(compute="_compute_category_change")

    # loose_or_master_carton = fields.Selection(
    #     [('master_carton', 'Master Carton'), ('loose', 'Loose')],
    #     string="Master Carton / Loose",
    #     help="Specify if the product is a master carton or loose"
    # )

    brand_id = fields.Many2one('product.brand', string="Brand", help="Brand of the product", tracking=True)

    product_model_name = fields.Char(string='Product Model Name',tracking=True)

    company_ids = fields.Many2many('res.company', string='Companies', required=True, readonly=False,
                                   default=lambda self: self.env.company,
                                   help="This product will appear only for users belonging to the chosen companies.")

    default_code = fields.Char('Internal Reference', compute='_compute_default_code', inverse='_set_default_code',
                               store=True, help="Unique internal reference (SKU) for identifying the product.",
                               tracking=True)

    # To change the default value of 'Track Inventory' selection field
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'By Quantity')],
        string="Tracking", required=True, default='serial',
        # Not having a default value here causes issues when migrating.
        compute='_compute_tracking', store=True, readonly=False, precompute=True,
        help="Ensure the traceability of a storable product in your warehouse.")

    active = fields.Boolean('Active', default=False,
                            help="If unchecked, it will allow you to hide the product without removing it.")

    @api.depends('is_storable')
    def _compute_tracking(self):
        self.filtered(lambda t: not t.is_storable and t.tracking != 'none').tracking = 'none'

    attribute_ids = fields.Many2many('product.attribute', tracking=True)

    # Activation status from variants (readonly, for display on template form)
    activation_status_display = fields.Char(
        string='Activation Status (Summary)',
        compute='_compute_activation_status_display',
        help='Shows activation status from variant(s). Updated via "Update Activation Status using CSV" wizard.'
    )

    @api.depends('product_variant_ids.activation_status')
    def _compute_activation_status_display(self):
        labels = {'active': 'Active', 'not_active': 'Not Active'}
        for rec in self:
            # mapped() returns a list, not a recordset
            statuses = [s for s in rec.product_variant_ids.mapped('activation_status') if s]
            if not statuses:
                rec.activation_status_display = ''
            elif len(set(statuses)) > 1:
                rec.activation_status_display = 'Mixed'
            else:
                rec.activation_status_display = labels.get(statuses[0], statuses[0] or '')

    # To check if mobile category is selected from the Category field
    @api.depends('categ_id')
    def _compute_category_change(self):
        mobile_categ = self.env.ref('ks_product_master.product_category_type_mobile', raise_if_not_found=False)
        packaging_categ = self.env.ref('ks_product_master.product_category_type_packaging_material',
                                       raise_if_not_found=False)

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

        variants = self.env['product.product'].with_context(active_test=False).search(
            [('product_tmpl_id', '=', self.id)])
        if variants:
            for variant in variants:
                variant.default_code = self._generate_sku(variant.id)
        else:
            self.default_code = self._generate_sku(self.id)

    def _generate_sku(self, varient_id):
        self.ensure_one()

        # Prefix
        # if self.loose_or_master_carton == 'master_carton':
        #     prefix = 'MC'
        # elif self.loose_or_master_carton == 'loose':
        #     prefix = 'L'
        # else:
        prefix = 'GEN'

        # Name
        name_part = (self.name or "").upper().replace(" ", "")

        # Attributes
        attr_part = ""
        variants = self.env['product.product'].with_context(active_test=False).search(
            [('product_tmpl_id', '=', self.id)])
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

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'consu':
            self.is_storable = True
            self.tracking = 'serial'

    # To set the product name in ALL CAPS based on model number
    @api.onchange('product_model_name')
    def _onchange_model(self):
        if self.product_model_name:
            self.name = self.product_model_name.upper()

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
            action['context'] = dict(action.get('context', {}), show_IMEI=show_IMEI_field, show_IMEI2=show_IMEI_field2)

        return action

    @api.model_create_multi
    def create(self, vals_list):

        # if packaging item then set is_storable and tracking to False, as if this enables then it requires serial number
        for vals in vals_list:
            categ_id = vals.get('categ_id')
            # packaging_categ = self.env.ref('ks_product_master.product_category_type_packaging_material',
            #                                raise_if_not_found=False)
            # if categ_id == packaging_categ.id:
            #     vals['tracking'] = 'none'

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
        # packaging_categ = self.env.ref('ks_product_master.product_category_type_packaging_material',
        #                                raise_if_not_found=False)
        # if categ_id == packaging_categ.id:
        #     vals['tracking'] = 'none'

        # 1. capitalize product name
        if vals.get('name'):
            vals['name'] = vals['name'].upper()

        res = super().write(vals)

        # 2. Trigger SKU generation if relevant fields are updated
        if any(field in vals for field in ['name', 'attribute_line_ids']):
            for rec in self:
                rec._generate_and_assign_sku()

        return res


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    activation_status = fields.Selection(
        selection=[('active', 'Active'), ('not_active', 'Not Active')],
        string='Activation Status',
        help='Mobile/tablet activation status. Updated only via "Update Activation Status using CSV" wizard.',
        readonly=True,
        tracking=True,
    )


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char(string="Brand Name", required=True)

