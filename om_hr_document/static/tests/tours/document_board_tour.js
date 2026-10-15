import { registry } from "@web/core/registry";

// The Documents tab of an employee: the cards, a missing type, and the dialog.
registry.category("web_tour.tours").add("om_hr_document_board", {
    steps: () => [
        {
            content: "open the Documents tab",
            trigger: '.o_notebook .nav-link:contains("Documents")',
            run: "click",
        },
        {
            content: "the passport card, expiring",
            trigger: '.o_om_document_card[data-state="expiring"]:contains("Passport")',
        },
        {
            content: "a type without document is offered",
            trigger: '.o_om_document_missing:contains("Work Permit")',
        },
        {
            content: "the expiring document can be renewed",
            trigger: '.o_om_document_card:contains("Passport") .o_om_document_renew',
        },
        {
            content: "add the missing work permit",
            trigger: '.o_om_document_missing:contains("Work Permit") .card-footer button',
            run: "click",
        },
        {
            content: "the dialog opens on a work permit",
            trigger: '.modal .o_field_widget[name="type_id"] input:value("Work Permit")',
        },
        {
            content: "fill the number",
            trigger: '.modal .o_field_widget[name="number"] input',
            run: "edit WP-42",
        },
        {
            content: "save the dialog",
            trigger: ".modal .o_form_button_save",
            run: "click",
        },
        {
            content: "the work permit is now a card",
            trigger: '.o_om_document_card:not(.o_om_document_missing):contains("WP-42")',
        },
    ],
});
