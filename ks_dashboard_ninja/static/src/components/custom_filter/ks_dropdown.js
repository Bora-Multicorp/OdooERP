/** @odoo-module **/

import { Component, xml, useEffect } from "@odoo/owl";
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";


export class KsDropDown extends Select{

    static props = [ ...Select.props, "activeOption"]
    static components = { Dropdown, DropdownItem }

    deserialize(value){
        return JSON.parse(value);
    }
}

KsDropDown.template = xml`<Dropdown menuClass="'o_input pe-3 text-truncate ks-dropdown-menu'">
                                <t t-set-slot="content">
                                    <DropdownItem t-foreach="props.options" t-as="option" t-key="serialize(option[0])" class="{ '': true }" t-esc="option[1]"
                                        onSelected="() => this.props.update(this.deserialize(serialize(option[0])))"/>
                                </t>
                                <button class="text-decoration-none" href="#" role="button" aria-expanded="false" t-out="props.activeOption"/>
                            </Dropdown>`





