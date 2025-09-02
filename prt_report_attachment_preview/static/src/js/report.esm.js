/** @odoo-module **/

import {WARNING_MESSAGE, WKHTMLTOPDF_MESSAGES, _getReportUrl} from "./tools.esm";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";
import {browser} from "@web/core/browser/browser";

let wkhtmltopdfStateProm = null;

registry.category("ir.actions.report handlers").add(
    "open_report_handler",
    async function (action, options, env) {
        if (action.type === "ir.actions.report" && action.report_type === "qweb-pdf") {
            // Check the state of wkhtmltopdf before proceeding
            if (!wkhtmltopdfStateProm) {
                wkhtmltopdfStateProm = rpc("/report/check_wkhtmltopdf");
            }
            const state = await wkhtmltopdfStateProm;
            if (state in WKHTMLTOPDF_MESSAGES) {
                env.services.notification.add(WKHTMLTOPDF_MESSAGES[state], {
                    sticky: true,
                    title: _t("Report"),
                });
            }
            if (state === "upgrade" || state === "ok") {
                // Trigger the download of the PDF report
                const url = _getReportUrl(action, "pdf", env);
                // AAB: this check should be done in get_file service directly,
                // should not be the concern of the caller (and that way, get_file
                // could return a deferred)
                try {
                    const newWindow = browser.open(url, "_blank");
                    if (!newWindow) {
                        env.services.notification.add(WARNING_MESSAGE, {
                            type: "warning",
                        });
                    }
                } catch {
                    env.services.notification.add(WARNING_MESSAGE, {
                        type: "warning",
                    });
                }
            }
            return true;
        }
        return false;
    },
    {sequence: 10}
);
