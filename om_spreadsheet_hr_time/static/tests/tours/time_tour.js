import { registry } from "@web/core/registry";

// The Time Off and Attendance dashboard opens, and every formula of its Data sheet evaluates without error.
registry.category("web_tour.tours").add("om_spreadsheet_hr_time", {
    steps: () => [
        {
            trigger: '.o_search_panel_category_value:contains("Time Off and Attendance")',
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
                const model = loader.getActiveDashboard().model;
                const sheetId = model.getters.getSheetIds().find(
                    (id) => model.getters.getSheetName(id) === "Data"
                );
                const worked = () => model.getters.getEvaluatedCell({ sheetId, col: 1, row: 4 }).value;
                for (let attempt = 0; attempt < 50 && typeof worked() !== "number"; attempt++) {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const errors = [];
                for (let row = 0; row < 22; row++) {
                    for (let col = 0; col < 4; col++) {
                        const cell = model.getters.getEvaluatedCell({ sheetId, col, row });
                        if (cell.type === "error") {
                            errors.push(`${col},${row}: ${cell.message || cell.value}`);
                        }
                    }
                }
                if (errors.length) {
                    throw new Error("Time formulas in error: " + errors.join("; "));
                }
                if (!(worked() > 0)) {
                    throw new Error("No hours worked: " + worked());
                }
            },
        },
    ],
});
