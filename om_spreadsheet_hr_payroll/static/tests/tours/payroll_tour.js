import { registry } from "@web/core/registry";

// The Payroll dashboard opens, and every formula of its Data sheet evaluates without error.
registry.category("web_tour.tours").add("om_spreadsheet_hr_payroll", {
    steps: () => [
        {
            trigger: '.o_search_panel_category_value:contains("Payroll")',
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
                const gross = () => model.getters.getEvaluatedCell({ sheetId, col: 1, row: 2 }).value;
                for (let attempt = 0; attempt < 50 && typeof gross() !== "number"; attempt++) {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const errors = [];
                for (let row = 0; row < 24; row++) {
                    for (let col = 0; col < 3; col++) {
                        const cell = model.getters.getEvaluatedCell({ sheetId, col, row });
                        if (cell.type === "error") {
                            errors.push(`${col},${row}: ${cell.message || cell.value}`);
                        }
                    }
                }
                if (errors.length) {
                    throw new Error("Payroll formulas in error: " + errors.join("; "));
                }
                if (!(gross() > 0)) {
                    throw new Error("No gross pay: " + gross());
                }
            },
        },
    ],
});
