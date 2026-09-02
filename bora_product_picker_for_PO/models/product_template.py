# -*- coding: utf-8 -*-
from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        res = []
        seen_tmpl_ids = set()
        if name:
            name_str = name.strip()
            # Differentiate between internal reference search vs product name search:
            # An internal reference search contains reference symbols (hyphens, underscores, digits) or exact code match.
            is_ref_search = '-' in name_str or '_' in name_str or any(c.isdigit() for c in name_str)
            if is_ref_search:
                variant_domain = ['|', ('default_code', '=ilike', name_str + '%'), ('barcode', '=ilike', name_str + '%')]
            else:
                variant_domain = ['|', ('default_code', '=ilike', name_str), ('barcode', '=ilike', name_str)]

            matching_variants = self.env['product.product'].search(variant_domain, limit=limit)
            seen_keys = set()
            for variant in matching_variants:
                code = variant.default_code or variant.barcode
                if not code:
                    continue
                tmpl = variant.product_tmpl_id
                if args:
                    filtered_tmpl = self.search([('id', '=', tmpl.id)] + args, limit=1)
                    if not filtered_tmpl:
                        continue
                variant_disp = variant.display_name or tmpl.display_name
                if variant_disp.startswith(f"[{code}]"):
                    disp_name = variant_disp
                elif variant_disp.startswith('['):
                    disp_name = variant_disp
                else:
                    disp_name = f"[{code}] {variant_disp}"
                key = (tmpl.id, disp_name)
                if key not in seen_keys:
                    seen_keys.add(key)
                    res.append(key)
                    seen_tmpl_ids.add(tmpl.id)
                if len(res) >= limit:
                    return res

        template_res = super().name_search(name=name, args=args, operator=operator, limit=limit)

        for item in template_res:
            if len(res) >= limit:
                break
            tmpl_id = item[0] if isinstance(item, tuple) else item
            if tmpl_id in seen_tmpl_ids:
                continue
            if isinstance(item, tuple):
                if item not in res:
                    res.append(item)
            elif isinstance(item, int):
                tmpl_rec = self.browse(item)
                item_tuple = (tmpl_rec.id, tmpl_rec.display_name)
                if item_tuple not in res:
                    res.append(item_tuple)

        return res



