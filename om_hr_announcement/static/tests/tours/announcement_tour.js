import { registry } from "@web/core/registry";

// The megaphone of the top bar counts the announcement waiting, which is acknowledged from its dropdown.
registry.category("web_tour.tours").add("om_hr_announcement_systray", {
    steps: () => [
        {
            trigger: ".o_om_announcement_menu .o_om_announcement_counter:contains(1)",
            run: "click",
        },
        {
            trigger: '.o_om_announcement_item:contains("Fire drill on Monday") button:contains("Acknowledge")',
            run: "click",
        },
        {
            content: "nothing waits any more",
            trigger: ".o_om_announcement_menu:not(:has(.o_om_announcement_counter))",
        },
    ],
});
