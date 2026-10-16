import { Component, onWillStart, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MODEL = "hr.announcement";
const { DateTime } = luxon;

/**
 * The megaphone of the top bar: the announcements waiting for the user,
 * unread or to acknowledge, the important ones first. Read or acknowledge
 * them from here.
 */
export class AnnouncementMenu extends Component {
    static components = { Dropdown };
    static template = "om_hr_announcement.AnnouncementMenu";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dropdown = useDropdownState();
        this.state = proxy({ count: 0, items: [] });
        onWillStart(() => this.load());
    }

    async load() {
        Object.assign(this.state, await this.orm.call(MODEL, "systray_data", []));
    }

    async open(item) {
        this.dropdown.close();
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: MODEL,
            res_id: item.id,
            views: [[false, "form"]],
            context: { form_view_ref: "om_hr_announcement.om_hr_announcement_view_form_reader" },
        }, { onClose: () => this.load() });
        await this.load();
    }

    async acknowledge(item) {
        await this.orm.call(MODEL, "action_acknowledge", [[item.id]]);
        await this.load();
    }

    formatDate(date) {
        return DateTime.fromISO(date).toLocaleString(DateTime.DATE_MED);
    }

    openAll() {
        this.dropdown.close();
        this.action.doAction("om_hr_announcement.om_hr_announcement_action_my");
    }
}

registry.category("systray").add("om_hr_announcement.menu", { Component: AnnouncementMenu }, { sequence: 25 });
