/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { getId } from "@web/model/relational_model/utils";
import { Component, useRef } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * Parse CSV text into rows of { lot_name, imei, imei2 }.
 * Expects 3 columns: Serials/Lots, IMEI 1, IMEI 2 (header row is skipped if present).
 */
function parseCsvSerialsImei(text) {
    const rows = [];
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const parts = parseCsvLine(line);
        if (parts.length >= 1) {
            const lot_name = (parts[0] || "").trim();
            const imei = (parts[1] !== undefined ? parts[1] : "").trim();
            const imei2 = (parts[2] !== undefined ? parts[2] : "").trim();
            if (i === 0 && isHeaderRow(lot_name, imei, imei2)) {
                continue;
            }
            if (lot_name) {
                rows.push({ lot_name, imei, imei2 });
            }
        }
    }
    return rows;
}

function isHeaderRow(col0, col1, col2) {
    const a = (col0 || "").toLowerCase();
    const b = (col1 || "").toLowerCase();
    const c = (col2 || "").toLowerCase();
    return (
        (a.includes("serial") || a.includes("lot")) &&
        (b.includes("imei") && (b === "imei 1" || b === "imei1" || b.includes("imei 1"))) &&
        (c.includes("imei") && (c === "imei 2" || c === "imei2" || c.includes("imei 2")))
    );
}

function parseCsvLine(line) {
    const result = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (c === '"') {
            inQuotes = !inQuotes;
        } else if (!inQuotes && (c === "," || c === "\t")) {
            result.push(current.trim());
            current = "";
        } else {
            current += c;
        }
    }
    result.push(current.trim());
    return result;
}

export class ImportSerialsCsvDialog extends Component {
    static template = "ks_product_master.ImportSerialsCsvDialog";
    static components = { Dialog };
    static props = {
        move: { type: Object },
        close: { type: Function },
    };

    setup() {
        this.size = "md";
        this.title = _t("Import Serials/Lots from CSV");
        this.fileInput = useRef("fileInput");
        this.keepLines = useRef("keepLines");
        this.orm = useService("orm");
    }

    async _onConfirm() {
        const fileInput = this.fileInput.el;
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            this.env.services.notification.add(
                _t("Please select a CSV file."),
                { type: "danger" }
            );
            return;
        }
        const file = fileInput.files[0];
        const text = await this._readFileAsText(file);
        const csvRows = parseCsvSerialsImei(text);
        if (csvRows.length === 0) {
            this.env.services.notification.add(
                _t("No valid rows found. CSV must have columns: Serials/Lots, IMEI 1, IMEI 2"),
                { type: "warning" }
            );
            return;
        }
        const context = {
            ...this.props.move.context,
            default_product_id: this.props.move.data.product_id[0],
            default_location_dest_id: this.props.move.data.location_dest_id[0],
            default_location_id: this.props.move.data.location_id[0],
            default_tracking: this.props.move.data.has_tracking,
            default_quantity: this.props.move.data.product_qty,
        };
        if (this.props.move.data.picking_type_id) {
            context.default_picking_type_id = this.props.move.data.picking_type_id[0];
        }
        if (this.props.move.data.company_id) {
            context.default_company_id = this.props.move.data.company_id[0];
        }
        let moveLineVals;
        try {
            moveLineVals = await this.orm.call(
                "stock.move",
                "action_generate_lot_line_vals_from_csv",
                [context, csvRows]
            );
        } catch (e) {
            this.env.services.notification.add(
                e.message || _t("Error generating lines from CSV."),
                { type: "danger" }
            );
            return;
        }
        const lines = this.props.move.data.move_line_ids;
        const newlines = [];
        for (const values of moveLineVals) {
            newlines.push(
                lines._createRecordDatapoint(values, {
                    mode: "readonly",
                    virtualId: getId("virtual"),
                    manuallyAdded: false,
                })
            );
        }
        if (!this.keepLines.el.checked) {
            await lines._applyCommands(
                lines._currentIds.map((currentId) => [x2ManyCommands.DELETE, currentId])
            );
        }
        lines.records.push(...newlines);
        lines._commands.push(
            ...newlines.map((record) => [x2ManyCommands.CREATE, record._virtualId])
        );
        lines._currentIds.push(...newlines.map((record) => record._virtualId));
        await lines._onUpdate();
        this.props.close();
    }

    _readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result || "");
            reader.onerror = () => reject(reader.error);
            reader.readAsText(file);
        });
    }
}

class ImportSerialsCsvButton extends Component {
    static template = "ks_product_master.ImportSerialsCsvButton";
    static props = { ...standardWidgetProps };

    setup() {
        this.dialog = useService("dialog");
    }

    openDialog() {
        this.dialog.add(ImportSerialsCsvDialog, {
            move: this.props.record,
        });
    }
}

registry
    .category("view_widgets")
    .add("import_lots_csv", { component: ImportSerialsCsvButton });
