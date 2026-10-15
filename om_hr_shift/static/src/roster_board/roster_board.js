import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const MODEL = "om.hr.shift";
const { DateTime } = luxon;

/**
 * The roster: the employees down the side, the days across, the shifts as
 * coloured chips. With a shift template chosen, a click on a cell plans it
 * there; a chip dragged to another cell moves the shift; a click on a chip
 * opens it. Time off and unavailability show in the cells, the warnings of
 * the shifts on their chips. Publishing writes the shifts on the working
 * schedules of the employees.
 */
export class RosterBoard extends Component {
    static template = "om_hr_shift.RosterBoard";
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        const monday = DateTime.local().startOf("week");
        this.state = proxy({
            dateFrom: monday,
            days: 7,
            departmentId: false,
            departments: [],
            templateId: false,
            data: { dates: [], employees: [], shifts: [], templates: [], can_edit: false },
            dragShift: null,
            dragOver: null,
            busy: false,
        });
        onWillStart(async () => {
            this.state.departments = await this.orm.searchRead("hr.department", [], ["id", "complete_name"], {
                order: "name",
            });
            await this.load();
        });
    }

    async load() {
        this.state.data = await this.orm.call(MODEL, "om_roster_data", [
            serializeDate(this.state.dateFrom),
            this.state.days,
            this.state.departmentId,
        ]);
    }

    async run(callback) {
        this.state.busy = true;
        try {
            await callback();
        } finally {
            this.state.busy = false;
        }
        await this.load();
    }

    // header

    get period() {
        const last = this.state.dateFrom.plus({ days: this.state.days - 1 });
        return `${this.state.dateFrom.toFormat("d MMM")} - ${last.toFormat("d MMM yyyy")}`;
    }

    move(step) {
        this.state.dateFrom = step
            ? this.state.dateFrom.plus({ days: step * this.state.days })
            : DateTime.local().startOf("week");
        return this.load();
    }

    setDays(days) {
        this.state.days = days;
        return this.load();
    }

    setDepartment(ev) {
        this.state.departmentId = parseInt(ev.target.value) || false;
        return this.load();
    }

    pickTemplate(template) {
        this.state.templateId = this.state.templateId === template.id ? false : template.id;
    }

    copyPrevious() {
        return this.run(async () => {
            const count = await this.orm.call(MODEL, "om_roster_copy_previous", [
                serializeDate(this.state.dateFrom),
                this.state.days,
                this.state.departmentId,
            ]);
            this.notification.add(_t("%s shifts copied as drafts.", count), { type: "info" });
        });
    }

    async publish() {
        const result = await this.orm.call(MODEL, "om_roster_publish", [
            serializeDate(this.state.dateFrom),
            this.state.days,
            this.state.departmentId,
        ]);
        if (result && typeof result === "object") {
            await this.action.doAction(result, { onClose: () => this.load() });
        } else {
            this.notification.add(_t("The shifts are published."), { type: "success" });
            await this.load();
        }
    }

    applyRotation() {
        return this.action.doAction("om_hr_shift.om_hr_shift_rotation_wizard_action", {
            additionalContext: { default_date_from: serializeDate(this.state.dateFrom) },
            onClose: () => this.load(),
        });
    }

    // grid

    get rows() {
        return [{ id: false, name: _t("Open Shifts"), department: "", hours: 0, off: {}, unavailable: {} }].concat(
            this.state.data.employees
        );
    }

    dayLabel(date) {
        return DateTime.fromISO(date).toFormat("ccc d");
    }

    isWeekend(date) {
        return DateTime.fromISO(date).weekday > 5;
    }

    isToday(date) {
        return date === DateTime.local().toISODate();
    }

    shiftsOf(row, date) {
        return this.state.data.shifts.filter((shift) => shift.employee_id === row.id && shift.date === date);
    }

    hours(value) {
        const minutes = Math.round(value * 60);
        return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, "0")}`;
    }

    onCellClick(row, date) {
        if (!this.state.data.can_edit || this.state.busy) {
            return;
        }
        if (!this.state.templateId) {
            this.notification.add(_t("Choose a shift above, then click the days to plan it."), { type: "info" });
            return;
        }
        return this.run(() =>
            this.orm.call(MODEL, "om_roster_assign", [row.id, date, this.state.templateId, this.state.departmentId])
        );
    }

    openShift(shift) {
        this.dialog.add(FormViewDialog, {
            resModel: MODEL,
            resId: shift.id,
            title: _t("Shift"),
            onRecordSaved: () => this.load(),
            removeRecord: () => this.load(),
        });
    }

    async deleteShift(shift) {
        await this.run(() => this.orm.unlink(MODEL, [shift.id]));
    }

    // drag and drop

    onDragStart(ev, shift) {
        if (!this.state.data.can_edit) {
            ev.preventDefault();
            return;
        }
        this.state.dragShift = shift;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", String(shift.id));
    }

    onDragOver(ev, row, date) {
        if (!this.state.dragShift) {
            return;
        }
        ev.preventDefault();
        this.state.dragOver = `${row.id}-${date}`;
    }

    onDragEnd() {
        this.state.dragShift = null;
        this.state.dragOver = null;
    }

    onDrop(ev, row, date) {
        ev.preventDefault();
        const shift = this.state.dragShift;
        this.onDragEnd();
        if (!shift || (shift.employee_id === row.id && shift.date === date)) {
            return;
        }
        return this.run(() => this.orm.call(MODEL, "om_roster_move", [shift.id, row.id, date]));
    }
}

registry.category("actions").add("om_hr_shift_roster", RosterBoard);
