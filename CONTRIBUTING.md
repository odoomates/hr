# Contributing to Odoo Mates HR

You are welcome here. Odoo Mates HR grows with the people who use it: every bug
report, review, fix, translation and idea makes it better for the next company.
You don't need to be an Odoo expert to help, and you are never on your own: ask,
and we guide you.

By taking part you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

- [Ways to help](#ways-to-help)
- [How to report a bug](#how-to-report-a-bug)
- [How to suggest a feature](#how-to-suggest-a-feature)
- [How to send a pull request](#how-to-send-a-pull-request)
- [Translations](#translations)
- [AI tools](#ai-tools)
- [License](#license)

## Ways to help

| You can… | How |
|---|---|
| **Try the apps and tell us** what works and what does not | [Open an issue](https://github.com/odoomates/hr/issues/new/choose), or write to [odoomates@gmail.com](mailto:odoomates@gmail.com) |
| **Review** a pull request | Read the [open pull requests](https://github.com/odoomates/hr/pulls), test them on your database, comment |
| **Fix a bug** or improve a module | Send a [pull request](#how-to-send-a-pull-request) |
| **Translate** the apps into your language | Edit the `i18n/<lang>.po` files: see [Translations](#translations) |
| **Improve the documentation** | The `README.rst` and the store page `static/description/index.html` of each module |
| **Spread the word** if you love it | Star the repository, rate the apps on the Odoo App Store, tell us your story at [odoomates@gmail.com](mailto:odoomates@gmail.com) |

First time? Look for the issues labelled
[good first issue](https://github.com/odoomates/hr/labels/good%20first%20issue),
or simply write to us: we help you find something that fits.

## How to report a bug

1. **Search first.** Look through the
   [open and closed issues](https://github.com/odoomates/hr/issues?q=is%3Aissue):
   the bug may already be known or fixed.
2. **Update.** Pull the latest commit of your branch, upgrade the module
   (`-u <module>`) and try again.
3. **Check where it comes from.** Try with only Odoo and the module installed. If
   it also happens without the module, it is a problem of Odoo or of another
   module, not of this repository.
4. **Open a [bug report](https://github.com/odoomates/hr/issues/new/choose)**
   and fill in the form:
   - the module and the Odoo version (branch);
   - the steps to reproduce, from a fresh database if you can (with or without
     demo data);
   - what you expected, and what happened instead;
   - the **full error and traceback**, as text, not as a screenshot. Find it in
     the error dialog (*Copy the full error to clipboard*) or in the server log;
   - screenshots, when the problem is in the screen or in a report.

No GitHub account? Send the same to
[odoomates@gmail.com](mailto:odoomates@gmail.com) with the subject
`[BUG] <module name>`.

**One issue for one problem.** Write in English if you can. Remove any employee
data, salary, password or token from the logs and screenshots: HR data is
personal data.

**Security problems are never reported in an issue:** follow
[SECURITY.md](SECURITY.md).

## How to suggest a feature

Open a [feature request](https://github.com/odoomates/hr/issues/new/choose), or
write to [odoomates@gmail.com](mailto:odoomates@gmail.com). Explain the business
need first (what your HR team is trying to do, and why, and the rules of your
country if they matter), then the solution you have in mind. A feature request is
not a promise: it is weighed against how many users need it and how much it costs
to maintain.

## How to send a pull request

For anything bigger than a small fix, **open an issue first** and agree on the
approach. This avoids work that cannot be merged, and we can point you to the
right place in the code.

### Steps

1. Fork the repository and create a branch from the version branch you fix,
   for example `20.0-fix-loan-installment`.
2. Make the change. Fix a bug on the oldest supported version that has it, and
   say in the pull request which newer versions need the same fix.
3. Add or update the tests (`tests/` of the module) and run them, as described in
   the [README](README.md#tests).
4. Open the pull request against the same version branch, and fill in the
   template.

### Code

- Follow the [Odoo coding guidelines](https://www.odoo.com/documentation/master/contributing/development/coding_guidelines.html)
  and the style of the module you change. The checks run ruff and pylint-odoo.
- Keep the change focused: no unrelated reformatting, no renamed files or
  fields "while you are there".
- Every module installs on its own. A feature that needs two modules goes in a
  small bridge module that installs itself once both are there, not in a new
  dependency.
- Every user-facing text is translatable: `_()` / `self.env._()` in Python,
  plain text in XML.
- Changes to the data model of a released module need a migration script in
  `migrations/<version>/`, and a higher `version` in `__manifest__.py`.
- New features need a few lines in the `README.rst` of the module. The
  maintainers update the store page from it.

### Commits

One commit per module and per logical change, written as in Odoo:

```text
[TAG] module: short summary of the change
```

- **Tags:** `[FIX]` bug fix, `[IMP]` improvement, `[ADD]` new module, `[REM]`
  removal, `[REF]` refactoring, `[I18N]` translations, `[MIG]` migration to a new
  version.
- The summary line is at most 50 characters, in English, without a full stop.
  For example: `[FIX] om_hr_loan: installment of the last month`.
- Add a body after a blank line only when the why is not obvious from the
  summary.
- Use `*` as the module when one change touches several modules:
  `[I18N] *: Spanish translations`.

### Review

A maintainer reviews the pull request. Answer the comments and push the
corrections to the same branch. Stuck? Ask in the pull request: we help you get
it over the line. A pull request without an answer for 30 days may be closed.

## Translations

Translations are the `i18n/<lang>.po` files of each module, made from the
`i18n/<module>.pot` template. Translating is one of the easiest ways to start,
and it opens the apps to every HR team speaking your language.

- To improve a translation, edit the `.po` file and send a pull request with an
  `[I18N]` commit.
- To add a language, copy the `.pot` file to `i18n/<lang>.po` (for example
  `fr.po`) and translate it.
- Don't edit the `.pot` file by hand: it is exported from Odoo when the module
  changes.
- Not at ease with Git? Send the `.po` file to
  [odoomates@gmail.com](mailto:odoomates@gmail.com) and we add it for you.

## AI tools

You may use AI tools to help you, but you remain responsible for everything you
submit. Read the [AI contribution policy](AI_POLICY.md) before you do.

## License

The modules are published under the
[GNU LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html) license, as declared
in the `__manifest__.py` of each module. By sending a contribution, you agree
that it is published under the same license.

---

Thank you for making Odoo Mates HR better. If you love it, let us know.

Always your Odoo Mates.
