# -*- coding: utf-8 -*-
from odoo import api, models


class StockTraceabilityReportInherit(models.TransientModel):
    _inherit = 'stock.traceability.report'

    def _make_dict_move(self, level, parent_id, move_line, unfoldable=False):
        """
        Override to add IMEI information to the traceability report lines.
        IMEI 1 is shown if product category is Mobile/Phone.
        IMEI 2 is shown if product category is Mobile/Phone AND is_dual_sim is True.
        """
        data = super()._make_dict_move(level, parent_id, move_line, unfoldable)

        # Get IMEI values and visibility flags from the move line
        product = move_line.product_id
        product_tmpl = product.product_tmpl_id

        # Check if product is in Mobile category
        is_mobile_category = product_tmpl.is_mobile_category_selected if hasattr(product_tmpl,
                                                                                 'is_mobile_category_selected') else False
        is_dual_sim = product_tmpl.is_dual_sim if hasattr(product_tmpl, 'is_dual_sim') else False

        # Get IMEI values from move_line
        imei_1 = move_line.imei if hasattr(move_line, 'imei') else False
        imei_2 = move_line.imei2 if hasattr(move_line, 'imei2') else False

        # Add IMEI data to the first (and only) dict in the data list
        if data:
            data[0].update({
                'imei_1': imei_1 if is_mobile_category else False,
                'imei_2': imei_2 if (is_mobile_category and is_dual_sim) else False,
                'show_imei_1': is_mobile_category,
                'show_imei_2': is_mobile_category and is_dual_sim,
            })

        return data

    @api.model
    def _final_vals_to_lines(self, final_vals, level):
        """
        Override to add IMEI data to the traceability report lines.
        IMEI columns are rendered separately in the template (not in the columns array).
        """
        lines = super()._final_vals_to_lines(final_vals, level)

        # Add IMEI data to each line for template rendering
        for i, data in enumerate(final_vals):
            if i < len(lines):
                lines[i].update({
                    'imei_1': data.get('imei_1', False),
                    'imei_2': data.get('imei_2', False),
                    'show_imei_1': data.get('show_imei_1', False),
                    'show_imei_2': data.get('show_imei_2', False),
                })

        return lines

    @api.model
    def get_lines(self, line_id=False, **kw):
        """
        Override to determine if IMEI columns should be shown globally in the report.
        This checks if any line in the current context has a mobile product.
        """
        lines = super().get_lines(line_id, **kw)

        # Determine global visibility for IMEI columns based on all lines
        any_show_imei_1 = any(line.get('show_imei_1', False) for line in lines)
        any_show_imei_2 = any(line.get('show_imei_2', False) for line in lines)

        # Add global visibility flags to each line for frontend use
        for line in lines:
            line['global_show_imei_1'] = any_show_imei_1
            line['global_show_imei_2'] = any_show_imei_2

        return lines

    @api.model
    def get_main_lines(self, given_context=None):
        """
        Override to include IMEI visibility context.
        """
        lines = super().get_main_lines(given_context)

        # Determine global visibility for IMEI columns
        any_show_imei_1 = any(line.get('show_imei_1', False) for line in lines)
        any_show_imei_2 = any(line.get('show_imei_2', False) for line in lines)

        # Add global flags to each line
        for line in lines:
            line['global_show_imei_1'] = any_show_imei_1
            line['global_show_imei_2'] = any_show_imei_2

        return lines
