import { registry } from "@web/core/registry";

// The Biometric Attendance dashboard opens, and every formula of its Data sheet evaluates without error.
registry.category("web_tour.tours").add("om_spreadsheet_hr_biometric", {
    steps: () => [
        {
            trigger: '.o_search_panel_category_value:contains("Biometric Attendance")',
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
                let model;
                for (let attempt = 0; attempt < 50 && !(model = loader.getActiveDashboard()?.model); attempt++) {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const sheetId = model.getters.getSheetIds().find(
                    (id) => model.getters.getSheetName(id) === "Data"
                );
                const punches = () => model.getters.getEvaluatedCell({ sheetId, col: 1, row: 0 }).value;
                for (let attempt = 0; attempt < 50 && typeof punches() !== "number"; attempt++) {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const errors = [];
                for (let row = 0; row < 4; row++) {
                    const cell = model.getters.getEvaluatedCell({ sheetId, col: 1, row });
                    if (cell.type === "error") {
                        errors.push(`${row}: ${cell.message || cell.value}`);
                    }
                }
                if (errors.length) {
                    throw new Error("Biometric formulas in error: " + errors.join("; "));
                }
                if (!(punches() > 0)) {
                    throw new Error("No punch: " + punches());
                }
            },
        },
    ],
});
