/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { useRef } from "@odoo/owl";

export class TodoEditDialog extends Component {
    static template = "todoEditDialog"
    static props = {
        close: Function,
        confirm: { type: Function },
        title: { type: String },
        inputText: { type: String }
    }
    static components = { Dialog }

    setup(){
        this.inputRef = useRef('inputRef')
    }

    onSave(ev){
        this.props.confirm(this.inputRef.el.value)
        this.props.close()
    }
}
