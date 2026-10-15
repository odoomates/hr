import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooEvaluationPlugin } from "@spreadsheet/plugins";
import { toServerDateString } from "@spreadsheet/helpers/helpers";

const { functionRegistry, evaluationPluginRegistry } = spreadsheet.registries;
const { arg, toJsDate, toString } = spreadsheet.helpers;

/**
 * The workforce of the companies selected in the company switcher on any date: the employees under contract,
 * those who joined or left, and their average service. Archived employees count in the past.
 */
export class OmHrPlugin extends OdooEvaluationPlugin {
    static getters = /** @type {const} */ (["getOmHrFigure"]);

    /**
     * @param {string} measure headcount, tenure, joiners or leavers
     * @param {string | false} dateFrom
     * @param {string | false} dateTo
     * @param {string} departments names separated by commas, empty for all
     * @returns {number}
     */
    getOmHrFigure(measure, dateFrom, dateTo, departments) {
        const result = this.getters.getServerData().batch.get("hr.version", "om_spreadsheet_fetch_hr", {
            measure,
            date_from: dateFrom,
            date_to: dateTo,
            departments,
        });
        return result.value;
    }
}

evaluationPluginRegistry.add("omHrFigures", OmHrPlugin);

function toServerDate(value, locale) {
    if (value?.value === undefined || value.value === null || value.value === "") {
        return false;
    }
    return toServerDateString(toJsDate(value, locale));
}

function toDepartments(value) {
    if (value?.value === undefined || value.value === null) {
        return "";
    }
    return toString(value);
}

const DEPARTMENTS = arg(
    "departments (string, optional)",
    _t('The names of the departments, separated by a comma, e.g. ODOO.FILTER.VALUE("Department"). Empty: all.')
);

functionRegistry.add("OM.HR.HEADCOUNT", {
    description: _t("Get the number of employees under contract on a date, for the selected companies."),
    args: [arg("date (date, optional)", _t("The day. Empty: today.")), DEPARTMENTS],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (date = { value: "" }, departments = { value: "" }) {
        const value = this.getters.getOmHrFigure(
            "headcount", false, toServerDate(date, this.locale), toDepartments(departments)
        );
        return { value, format: "#,##0" };
    },
});

functionRegistry.add("OM.HR.TENURE", {
    description: _t("Get the average service, in years, of the employees under contract on a date."),
    args: [arg("date (date, optional)", _t("The day. Empty: today.")), DEPARTMENTS],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (date = { value: "" }, departments = { value: "" }) {
        const value = this.getters.getOmHrFigure(
            "tenure", false, toServerDate(date, this.locale), toDepartments(departments)
        );
        return { value, format: "0.0" };
    },
});

for (const [name, measure, description] of [
    ["OM.HR.JOINERS", "joiners", _t("Get the number of employees whose contract started between two dates.")],
    ["OM.HR.LEAVERS", "leavers", _t("Get the number of employees whose contract ended between two dates.")],
]) {
    functionRegistry.add(name, {
        description,
        args: [
            arg("date_from (date)", _t("The first day.")),
            arg("date_to (date)", _t("The last day.")),
            DEPARTMENTS,
        ],
        category: "Odoo",
        returns: ["NUMBER"],
        compute: function (dateFrom, dateTo, departments = { value: "" }) {
            const value = this.getters.getOmHrFigure(
                measure,
                toServerDate(dateFrom, this.locale),
                toServerDate(dateTo, this.locale),
                toDepartments(departments)
            );
            return { value, format: "#,##0" };
        },
    });
}
