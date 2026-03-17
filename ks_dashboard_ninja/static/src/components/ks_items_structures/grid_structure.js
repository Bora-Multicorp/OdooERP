import { Component, xml, useState, useEffect } from "@odoo/owl"
import { Dialog } from "@web/core/dialog/dialog";

/*
*   Wrapper for KsItems component to show in Dialog In Row Mode
*/
export class KSItemsGridStructure extends Component{

    static template = xml`<Dialog size="'lg'" title="'Generate With AI'" footer="false">
                                <div class='ks-modal-height-limits'>
                                    <t t-component='props.componentInfo.component' t-props='props.componentInfo.props'/>
                                </div>
                          </Dialog>`

    static props = {
        componentInfo: { type: Object },
        close: { type: Function, optional: true}
    }

    static components = { Dialog }

    static defaultProps = {
        close: () => {}
    }

    setup(){
        this.state = useState({
            isLoading: true
        })

        useEffect( () => { this.state.isLoading = false })
    }
}