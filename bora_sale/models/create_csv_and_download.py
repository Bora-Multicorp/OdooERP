from odoo import models
import base64
import csv
import io


class StockMove(models.Model):
    _inherit = "stock.move"


    def create_csv_and_download(self):
        self.ensure_one()

        filename = self._get_csv_filename()
        csv_content = self._prepare_csv_content()
        attachment = self._create_attachment(filename, csv_content, self._name, self.id)

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def create_csv_and_save_in_order_documents(self):
        self.ensure_one()

        # Find the related Sale Order
        sale_order = self.picking_id.sale_id

        # Build file
        filename = self._get_csv_filename()
        csv_content = self._prepare_csv_content()

        # Save as attachment
        self._create_attachment(filename, csv_content, 'sale.order', sale_order.id)

        # Throw a notification
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'info',
                'title': "Document has been successfully saved in the order's documents section.",
                'message':  '',
                'sticky': True,
            },
        )

    def _get_csv_filename(self):
        self.ensure_one()
        if self.picking_id:
            return f"{self.picking_id.name.replace('/', '_')}_IMEI_Serials.csv"
        return f"{self.product_id.name.replace(' ', '_')}_IMEI_Serials.csv"

    def _prepare_csv_content(self):
        self.ensure_one()
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # --- Step 1: Check availability of each column ---
        has_product_name = any(line.product_id.product_tmpl_id.name for line in self.move_line_ids)
        has_type = any(line.product_id.product_tmpl_id.categ_id or line.product_id.product_tmpl_id.brand_id for line in self.move_line_ids)
        has_serial = any(line.lot_id.name for line in self.move_line_ids)
        has_imei1 = any(getattr(line, "imei", False) for line in self.move_line_ids)
        has_imei2 = any(getattr(line, "imei2", False) for line in self.move_line_ids)
        has_model = any(line.product_id.product_tmpl_id.model for line in self.move_line_ids)
        has_variant = any(line.product_id.product_template_attribute_value_ids for line in self.move_line_ids)
        has_sku = any(line.product_id.default_code for line in self.move_line_ids)

        # --- Step 2: Build header dynamically ---
        headers = []
        if has_product_name:
            headers.append("Product Name")
        if has_type:
            headers.append("Type")
        if has_serial:
            headers.append("Serial Number")
        if has_imei1:
            headers.append("IMEI1")
        if has_imei2:
            headers.append("IMEI2")
        if has_model:
            headers.append("Model")
        if has_variant:
            headers.append("Variant Info")
        if has_sku:
            headers.append("SKU")

        writer.writerow(headers)

        # --- Step 3: Write rows dynamically ---
        for line in self.move_line_ids:
            product = line.product_id
            template = product.product_tmpl_id

            row = []
            if has_product_name:
                row.append(template.name or "")
            if has_type:
                category_brand = template.categ_id.name or ""
                if template.brand_id:
                    category_brand = f"{category_brand} ({template.brand_id.name})"
                row.append(category_brand)
            if has_serial:
                row.append(line.lot_id.name or "")
            if has_imei1:
                row.append(line.imei or "")
            if has_imei2:
                row.append(line.imei2 or "")
            if has_model:
                row.append(template.model or "")
            if has_variant:
                variant_info = []
                for ptav in product.product_template_attribute_value_ids:
                    attribute = ptav.attribute_id.name
                    value = ptav.product_attribute_value_id.name
                    variant_info.append(f"{attribute}: {value}")
                row.append(", ".join(variant_info))
            if has_sku:
                row.append(product.default_code or "")

            writer.writerow(row)

        # --- Step 4: Return CSV ---
        csv_content = buffer.getvalue()
        buffer.close()
        return csv_content
    
    def _create_attachment(self, filename, csv_content, res_model, res_id):
        return self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(csv_content.encode("utf-8")),
            'res_model': res_model,
            'res_id': res_id,
            'mimetype': 'text/csv',
        })