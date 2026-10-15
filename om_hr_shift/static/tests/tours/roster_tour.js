import { registry } from "@web/core/registry";

// A shift planned on the roster in two clicks, then published.
registry.category("web_tour.tours").add("om_hr_shift_roster", {
    steps: () => [
        {
            trigger: '.o_om_roster_template:contains("Morning")',
            run: "click",
        },
        {
            content: "plan the morning on the first day of the employee",
            trigger: 'tr:has(.o_om_roster_name:contains("Roster Tour")) td.o_om_roster_cell:eq(0)',
            run: "click",
        },
        {
            trigger: 'tr:has(.o_om_roster_name:contains("Roster Tour")) .o_om_shift_chip.o_om_draft:contains("M")',
        },
        {
            trigger: ".o_om_roster_publish",
            run: "click",
        },
        {
            content: "published: no longer dashed",
            trigger: 'tr:has(.o_om_roster_name:contains("Roster Tour")) .o_om_shift_chip:not(.o_om_draft)',
        },
    ],
});
