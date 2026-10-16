import { registry } from "@web/core/registry";

// The Talent and Compliance dashboard opens, and every formula of its Data sheet evaluates without error.
registry.category("web_tour.tours").add("om_spreadsheet_hr_talent", {
    steps: () => [
        {
            trigger: '.o_search_panel_category_value:contains("Talent and Compliance")',
            run: "click",
        },
        {
            trigger: ".o_spreadsheet_dashboard_action .o-grid",
        },
        {
            content: "the figures are computed",
            trigger: ".o_spreadsheet_dashboard_action",
            run: async () => {
                const loader = odoo.__WOWL_DEBUG__.root.env.services.spreadsheet_dashboard_loader;
                // the dashboard and its data load after its action shows: wait for them
                let model;
                for (let attempt = 0; attempt < 50 && !(model = loader.getActiveDashboard()?.model); attempt++) {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const sheetId = model.getters.getSheetIds().find(
                    (id) => model.getters.getSheetName(id) === "Data"
                );
                const cell = (row) => model.getters.getEvaluatedCell({ sheetId, col: 1, row });
                for (let attempt = 0; attempt < 50 && typeof cell(0).value !== "number"; attempt++) {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const errors = [];
                for (let row = 0; row < 6; row++) {
                    if (cell(row).type === "error" || typeof cell(row).value !== "number") {
                        errors.push(`${row}: ${cell(row).message || cell(row).value}`);
                    }
                }
                if (errors.length) {
                    throw new Error("Talent formulas in error: " + errors.join("; "));
                }
                if (!(cell(0).value >= 1 && cell(2).value >= 1)) {
                    throw new Error(`Expected an appraisal to do and a document expiring: ${cell(0).value}, ${cell(2).value}`);
                }
            },
        },
    ],
});
