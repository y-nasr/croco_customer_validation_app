# Customer Mobile Validation

Frappe/ERPNext app that enforces consistent mobile-number handling on the
Customer doctype:

- Stores numbers in **E.164** format (`+CC<national-number>`).
- **Quick-entry country-code picker** with 72 countries (alphabetized) and
  per-country placeholder examples.
- **Server-side validation** via the `phonenumbers` library. Rejects landlines
  (`FIXED_LINE`) and anything that's not a valid phone number.
- **Cross-Customer duplicate detection**: any save (add or edit) whose
  national-subscriber number matches another Customer is refused with a
  `DuplicateEntryError` that names the existing record(s). As a side effect,
  the existing record's stored format is opportunistically migrated to the
  clean `+CC...` form.
- **Bidirectional sync** between `mobile_no` and a custom `custom_mobile_intl`
  field so quick-entry and full-form writes always end up consistent.
- All behavior is **gated behind a single feature flag** that the
  Administrator can toggle from the Customer list page — changes propagate
  in real time to every connected desk session.

## Install

```bash
bench get-app https://github.com/<your-org>/customer_mobile_validation
bench --site <site> install-app customer_mobile_validation
bench restart
```

The `after_install` hook creates the `custom_mobile_intl` Custom Field on
Customer; nothing else needs manual setup.

## License

MIT
