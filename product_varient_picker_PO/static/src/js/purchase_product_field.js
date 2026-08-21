/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useEffect } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import {
    ProductLabelSectionAndNoteField,
    productLabelSectionAndNoteField,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";

function getSelectedCustomPtav(ptal) {
    return ptal.attribute_values.find(
        ptav => ptav.is_custom && ptal.selected_attribute_value_ids.includes(ptav.id)
    );
}

async function applyProductToPOLine(record, product) {
    const customAttributesCommands = [
        x2ManyCommands.set([]),
    ];
    if (product.attribute_lines) {
        for (const ptal of product.attribute_lines) {
            const selectedCustomPTAV = getSelectedCustomPtav(ptal);
            if (selectedCustomPTAV) {
                customAttributesCommands.push(
                    x2ManyCommands.create(undefined, {
                        custom_product_template_attribute_value_id: [selectedCustomPTAV.id, "we don't care"],
                        custom_value: ptal.customValue,
                    })
                );
            }
        }
    }

    const noVariantPTAVIds = product.attribute_lines ? product.attribute_lines.filter(
        ptal => ptal.create_variant === "no_variant"
    ).flatMap(ptal => ptal.selected_attribute_value_ids) : [];

    await record._update({
        product_id: [product.id, product.display_name],
        product_qty: product.quantity || record.data.product_qty || 1.0,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
    });
}

export class PurchaseOrderLineProductField extends ProductLabelSectionAndNoteField {
    static template = "product_varient_picker_PO.PurchaseProductField";
    static props = {
        ...ProductLabelSectionAndNoteField.props,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");

        let isMounted = false;
        let isInternalUpdate = false;
        const { updateRecord } = this;
        this.updateRecord = (value) => {
            isInternalUpdate = true;
            return updateRecord.call(this, value);
        };

        useEffect(value => {
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                if (this.relation === "product.template") {
                    this._onProductTemplateUpdate();
                }
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

    get productName() {
        if (this.props.name === 'product_template_id') {
            const product_id_data = this.props.record.data.product_id;
            if (product_id_data && product_id_data[1]) {
                return product_id_data[1].split("\n")[0];
            }
        }
        return super.productName;
    }

    get hasConfigurationButton() {
        return this.isConfigurableTemplate;
    }

    get isConfigurableTemplate() {
        return Boolean(this.props.record.data.is_configurable_product);
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }

    async _onProductTemplateUpdate() {
        if (!this.props.record.data.product_template_id) {
            return;
        }

        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
            { context: this.context }
        );

        if (result && result.product_id) {
            if (!this.props.record.data.product_id || this.props.record.data.product_id[0] !== result.product_id.id) {
                await this.props.record.update({
                    product_id: [result.product_id.id, result.product_name],
                });
            }
        } else {
            this._openProductConfigurator(false);
        }
    }

    onEditConfiguration() {
        if (this.isConfigurableTemplate) {
            this._openProductConfigurator(true);
        }
    }

    async _openProductConfigurator(edit = false) {
        const purchaseOrderRecord = this.props.record.model.root;
        const purchaseOrderLine = this.props.record.data;

        if (!purchaseOrderLine.product_template_id) {
            return;
        }

        let ptavIds = this._getVariantPtavIds(purchaseOrderLine);
        let customPtavs = [];

        if (edit) {
            ptavIds.push(...this._getNoVariantPtavIds(purchaseOrderLine));
            customPtavs = await this._getCustomPtavs(purchaseOrderLine);
        }

        const dateOrder = purchaseOrderRecord.data.date_order
            ? serializeDateTime(purchaseOrderRecord.data.date_order)
            : serializeDateTime(new Date());

        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: purchaseOrderLine.product_template_id[0],
            ptavIds: ptavIds,
            customPtavs: customPtavs,
            quantity: purchaseOrderLine.product_qty || 1.0,
            productUOMId: purchaseOrderLine.product_uom ? purchaseOrderLine.product_uom[0] : null,
            companyId: purchaseOrderRecord.data.company_id ? purchaseOrderRecord.data.company_id[0] : null,
            currencyId: purchaseOrderLine.currency_id
                ? purchaseOrderLine.currency_id[0]
                : (purchaseOrderRecord.data.currency_id ? purchaseOrderRecord.data.currency_id[0] : null),
            soDate: dateOrder,
            edit: edit,
            onlyMainProduct: true,
            save: async (mainProduct) => {
                await applyProductToPOLine(this.props.record, mainProduct);
                purchaseOrderRecord.data.order_line.leaveEditMode();
            },
            discard: () => {
                if (!edit) {
                    purchaseOrderRecord.data.order_line.delete(this.props.record);
                }
            },
        });
    }

    _getVariantPtavIds(purchaseOrderLine) {
        return purchaseOrderLine.product_template_attribute_value_ids && purchaseOrderLine.product_template_attribute_value_ids.records
            ? purchaseOrderLine.product_template_attribute_value_ids.records.map(record => record.resId)
            : [];
    }

    _getNoVariantPtavIds(purchaseOrderLine) {
        return purchaseOrderLine.product_no_variant_attribute_value_ids && purchaseOrderLine.product_no_variant_attribute_value_ids.records
            ? purchaseOrderLine.product_no_variant_attribute_value_ids.records.map(record => record.resId)
            : [];
    }

    async _getCustomPtavs(purchaseOrderLine) {
        const customPtavIds = purchaseOrderLine.product_custom_attribute_value_ids;
        if (!customPtavIds) return [];
        const customPtavs = customPtavIds.records && customPtavIds.records[0]?.isNew
            ? customPtavIds.records.map(record => record.data)
            : customPtavIds.currentIds && customPtavIds.currentIds.length
                ? await this.orm.read(
                    'product.attribute.custom.value',
                    customPtavIds.currentIds,
                    ['custom_product_template_attribute_value_id', 'custom_value'],
                )
                : [];
        return customPtavs.map(customPtav => ({
            id: customPtav.custom_product_template_attribute_value_id[0],
            value: customPtav.custom_value,
        }));
    }
}

export const purchaseOrderLineProductField = {
    ...productLabelSectionAndNoteField,
    component: PurchaseOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = productLabelSectionAndNoteField.extractProps(...arguments);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category("fields").add("pol_product_many2one", purchaseOrderLineProductField, { force: true });
registry.category("fields").add("pol_product_variant_picker", purchaseOrderLineProductField, { force: true });
