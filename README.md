# Odoo Mates HR

The HR suite of Odoo Mates for **Odoo 20 Community**: payroll, time and attendance, shifts, employee
self-service and the whole employee lifecycle, with or without Accounting.

Every module works on its own and installs only what it needs. Install **Odoo Mates HR** (`om_hrms`) for the
whole suite, or only the modules you need, e.g. HR Loans alone. The links between modules, e.g. loans deducted
from the payslips, install by themselves once both sides are there.

## Requirements

- Odoo 20.0 Community Edition. No Enterprise module and no external Python library.
- Accounting is optional: the accounting links (payroll entries, loans in accounting, salary payments) install
  when Accounting is there.

## Modules

### Payroll

| Module | What it does |
|---|---|
| `om_hr_payroll` | Salary structures, rules, components, parameters and brackets; payslips and batches; pay on the working schedule or on work entries, attendances and time off, monthly or hourly; retro pay; My Payslips for the employees |
| `om_hr_payroll_account` | Journal entries of the payslips and the salary payments (installs Accounting) |
| `om_hr_payroll_adjustment` | Bonuses, commissions, fines, court deductions: once, for some months or until a total, fixed or a percentage, each type on its own payslip line |
| `om_hr_payroll_export`, `om_file_layout` | Salary transfer files in the layout of your bank (CSV, fixed width, Excel), e.g. WPS |
| `om_hr_overtime_payroll` | Validated overtime paid at the rate of each time rule |
| `om_hr_shift_payroll` | Shift allowances, e.g. a night shift allowance |
| `om_hr_lateness_payroll` | Lateness penalties of the month taken off the payslips |

### Time, attendance and shifts

| Module | What it does |
|---|---|
| `om_hr_shift` | Shift templates, a roster board, rotations, open shifts, shift swaps and availability, with checks for time off, rest and weekly hours; published shifts become the working schedule |
| `om_hr_lateness` | Late arrivals and early departures against the schedule, grace minutes, a penalty matrix, warnings and excuses |
| `om_hr_overtime_request` | Overtime authorised in advance; beyond it, the manager accepts or rejects it |

### Employee lifecycle

| Module | What it does |
|---|---|
| `om_hr_loan` | Loans and salary advances, approved and repaid in installments (with `om_hr_loan_payroll`, `om_hr_loan_account`) |
| `om_hr_exit`, `om_hr_gratuity`, `om_hr_exit_payroll` | Resignations and terminations, clearance checklist, end of service gratuity, final settlement with leave encashment |
| `om_hr_appraisal` | Self assessment, manager review, goals, probation reviews and review cycles |
| `om_hr_asset` | Assets in the hands of the employees, handover forms, charges for lost assets (installs Maintenance) |
| `om_hr_reminder` | Birthdays, work anniversaries and probation ends through the Automation Rules |

### Documents, letters and approvals

| Module | What it does |
|---|---|
| `om_document`, `om_hr_document` | Documents with expiry dates and reminders: passports, visas, permits, IDs |
| `om_print_template`, `om_hr_certificate` | Certificates and letters from templates: salary, employment, experience, NOC, with an optional verification QR code |
| `om_approval`, `om_hr_approval` | Multi-step approval flows for any app, and HR requests |

### Self-service and dashboards

| Module | What it does |
|---|---|
| `om_hr_base` | My HR for the employees: their payslips, loans, documents, shifts, requests and the celebrations of the month |
| `om_hr_portal` and `om_hr_portal_*` | The same on the website portal, for employees without a backend user |
| `om_spreadsheet_hr*` | Workforce, Payroll, Time Off and Attendance, Talent and Compliance dashboards |

## Installation

1. Clone the branch of your Odoo version into a folder of your addons path:
   `git clone -b 20.0 https://github.com/odoomates/hr.git`
2. Update the Apps list and install **Odoo Mates HR**, or the modules you need.

## Support

Odoo Mates — odoomates@gmail.com. License: LGPL-3.
