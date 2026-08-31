/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { saleOrderLineProductField } from '@sale/js/sale_product_field';
import { ProductConfiguratorDialog } from '@sale/js/product_configurator_dialog/product_configurator_dialog';

export class PurchaseOrderLineProductField extends saleOrderLineProductField.component {
    static template = 'purchase.PurchaseProductField';

    setup() {
        super.setup();
        this.dialog = useService('dialog');
    }

    get configurationButtonHelp() {
        return 'Edit Configuration';
    }

    async _openProductConfigurator(edit = false) {
        const purchaseOrderRecord = this.props.record.model.root;
        const purchaseOrderLine = this.props.record.data;
        let ptavIds = this._getVariantPtavIds(purchaseOrderLine);
        let customPtavs = [];

        if (edit) {
            ptavIds.push(...this._getNoVariantPtavIds(purchaseOrderLine));
            customPtavs = await this._getCustomPtavs(purchaseOrderLine);
        }

        const productTemplateId = Array.isArray(purchaseOrderLine.product_template_id)
            ? purchaseOrderLine.product_template_id[0]
            : (purchaseOrderLine.product_template_id?.id || purchaseOrderLine.product_template_id || false);

        const productUOMId = Array.isArray(purchaseOrderLine.product_uom)
            ? purchaseOrderLine.product_uom[0]
            : (purchaseOrderLine.product_uom?.id || purchaseOrderLine.product_uom || false);

        const companyId = Array.isArray(purchaseOrderRecord.data.company_id)
            ? purchaseOrderRecord.data.company_id[0]
            : (purchaseOrderRecord.data.company_id?.id || purchaseOrderRecord.data.company_id || false);

        const pricelistId = purchaseOrderRecord.data.pricelist_id
            ? (Array.isArray(purchaseOrderRecord.data.pricelist_id) ? purchaseOrderRecord.data.pricelist_id[0] : purchaseOrderRecord.data.pricelist_id)
            : false;

        const currencyId = Array.isArray(purchaseOrderLine.currency_id)
            ? purchaseOrderLine.currency_id[0]
            : (Array.isArray(purchaseOrderRecord.data.currency_id)
                ? purchaseOrderRecord.data.currency_id[0]
                : false);

        const quantity = purchaseOrderLine.product_qty || purchaseOrderLine.product_uom_qty || 1;

        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId,
            ptavIds,
            customPtavs,
            quantity,
            productUOMId,
            companyId,
            pricelistId,
            currencyId,
            soDate: purchaseOrderRecord.data.date_order,
            edit,
            save: async (mainProduct, optionalProducts) => {
                const line = this.props.record;
                await Promise.all([
                    line._update({
                        product_id: [mainProduct.id, mainProduct.display_name],
                        product_qty: mainProduct.quantity,
                    }),
                    ...optionalProducts.map(async product => {
                        const newLine = await purchaseOrderRecord.data.order_line.addNewRecord({ position: 'bottom', mode: 'readonly' });
                        await newLine._update({
                            product_id: [product.id, product.display_name],
                            product_qty: product.quantity,
                        });
                    }),
                ]);
                purchaseOrderRecord.data.order_line.leaveEditMode();
            },
            discard: () => {
                purchaseOrderRecord.data.order_line.delete(this.props.record);
            },
        });
    }
}

export const purchaseOrderLineProductField = {
    ...saleOrderLineProductField,
    component: PurchaseOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = saleOrderLineProductField.extractProps(fieldInfo, dynamicInfo);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category('fields').add('pol_product_many2one', purchaseOrderLineProductField);
