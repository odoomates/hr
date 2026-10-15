import { registry } from "@web/core/registry";

// The Workforce dashboard opens, and every formula of its Data sheet evaluates without error.
registry.category("web_tour.tours").add("om_spreadsheet_hr_workforce", {
    steps: () => [
        {
            trigger: '.o_search_panel_category_value:contains("Workforce")',
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
                for (let attempt = 0; attempt < 50; attempt++) {
                    const cell = model.getters.getEvaluatedCell({ sheetId, col: 1, row: 4 });
                    if (typeof cell.value === "number") {
                        break;
                    }
                    await new Promise((resolve) => setTimeout(resolve, 200));
                }
                const errors = [];
                for (let row = 0; row < 26; row++) {
                    for (let col = 0; col < 5; col++) {
                        const cell = model.getters.getEvaluatedCell({ sheetId, col, row });
                        if (cell.type === "error") {
                            errors.push(`${col},${row}: ${cell.message || cell.value}`);
                        }
                    }
                }
                if (errors.length) {
                    throw new Error("Workforce formulas in error: " + errors.join("; "));
                }
                const headcount = model.getters.getEvaluatedCell({ sheetId, col: 1, row: 4 }).value;
                if (typeof headcount !== "number" || headcount < 1) {
                    throw new Error("No headcount: " + headcount);
                }
            },
        },
    ],
});
