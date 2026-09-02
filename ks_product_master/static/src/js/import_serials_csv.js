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
 * Parse CSV text into rows of { lot_name, imei, imei2, made_in }.
 * Supports columns: Serials/Lots, IMEI 1, IMEI 2, Made In (header row optional).
 */
function parseCsvSerialsImei(text) {
    const rows = [];
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (lines.length === 0) return rows;

    const parsedLines = lines.map(parseCsvLine);
    const firstRow = parsedLines[0];
    const hasHeader = isHeaderRow(firstRow);

    let headerMap = null;
    let dataLines = parsedLines;
    if (hasHeader) {
        headerMap = mapHeaderIndices(firstRow);
        dataLines = parsedLines.slice(1);
    }

    for (const parts of dataLines) {
        if (!parts || parts.length === 0) continue;
        const rowData = extractRowData(parts, headerMap);
        if (rowData.lot_name) {
            rows.push(rowData);
        }
    }
    return rows;
}

function isHeaderRow(row) {
    if (!row || row.length === 0) return false;
    const rowStr = row.map((c) => (c || "").toLowerCase()).join(" ");
    return (
        rowStr.includes("serial") ||
        rowStr.includes("lot") ||
        rowStr.includes("imei") ||
        rowStr.includes("made") ||
        rowStr.includes("country")
    );
}

function mapHeaderIndices(headers) {
    let lot_idx = -1;
    let imei1_idx = -1;
    let imei2_idx = -1;
    let made_in_idx = -1;

    headers.forEach((h, idx) => {
        const hClean = (h || "").trim().toLowerCase();
        if (!hClean) return;
        if ((hClean.includes("serial") || hClean.includes("lot")) && lot_idx === -1) {
            lot_idx = idx;
        } else if ((hClean.includes("imei 2") || hClean.includes("imei2") || hClean.includes("imei_2")) && imei2_idx === -1) {
            imei2_idx = idx;
        } else if ((hClean.includes("imei 1") || hClean.includes("imei1") || hClean.includes("imei_1") || hClean === "imei") && imei1_idx === -1) {
            imei1_idx = idx;
        } else if ((hClean.includes("made") || hClean.includes("country") || hClean.includes("origin")) && made_in_idx === -1) {
            made_in_idx = idx;
        }
    });

    if (lot_idx === -1 && headers.length > 0) {
        lot_idx = 0;
    }

    return { lot_idx, imei1_idx, imei2_idx, made_in_idx };
}

function extractRowData(parts, headerMap) {
    const getVal = (idx) => (idx !== -1 && idx < parts.length && parts[idx] !== undefined ? String(parts[idx]).trim() : "");

    if (headerMap) {
        return {
            lot_name: getVal(headerMap.lot_idx),
            imei: getVal(headerMap.imei1_idx),
            imei2: getVal(headerMap.imei2_idx),
            made_in: getVal(headerMap.made_in_idx),
        };
    } else {
        const lot_name = getVal(0);
        let imei = "";
        let imei2 = "";
        let made_in = "";
        if (parts.length >= 4) {
            imei = getVal(1);
            imei2 = getVal(2);
            made_in = getVal(3);
        } else if (parts.length === 3) {
            const p1 = getVal(1);
            const p2 = getVal(2);
            if (/^\d+$/.test(p1) && /^\d+$/.test(p2)) {
                imei = p1;
                imei2 = p2;
            } else if (/^\d+$/.test(p1)) {
                imei = p1;
                made_in = p2;
            } else {
                made_in = p1;
            }
        } else if (parts.length === 2) {
            const p1 = getVal(1);
            if (/^\d+$/.test(p1)) {
                imei = p1;
            } else {
                made_in = p1;
            }
        }
        return { lot_name, imei, imei2, made_in };
    }
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
                _t("No valid rows found. CSV must have columns: Serials/Lots, IMEI 1, IMEI 2, Made In"),
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
