import frappe
from frappe import _


# ─── Feature flag ────────────────────────────────────────────────────────────
# Toggle the entire feature (server validation + dedup + sync + JS picker).
# The flag is toggled from the Customer list page menu (Administrator only)
# and persisted as a global default in the DB. As a fallback, it can also be
# set in site_config.json:
#
#     "customer_mobile_validation_enabled": 0   # disable everything
#
# Resolution order: DB default → site_config.json → True (default)
_FLAG_KEY = "customer_mobile_validation_enabled"


def _is_enabled():
    db_val = frappe.db.get_default(_FLAG_KEY)
    if db_val is not None and str(db_val) != "":
        return str(db_val).strip() not in ("0", "false", "False", "no", "No")
    return bool(frappe.local.conf.get(_FLAG_KEY, 1))


def boot_customer_mobile(bootinfo):
    """Expose the feature flag to client-side JS via frappe.boot."""
    bootinfo[_FLAG_KEY] = _is_enabled()


@frappe.whitelist()
def get_customer_mobile_validation_status():
    return {"enabled": _is_enabled()}


@frappe.whitelist()
def set_customer_mobile_validation_status(enabled):
    if (frappe.session.user or "").lower() != "administrator":
        frappe.throw(
            _("Only the Administrator can change this setting."),
            frappe.PermissionError,
        )
    val = "1" if str(enabled).strip() in ("1", "true", "True", "yes", "Yes") else "0"
    frappe.db.set_default(_FLAG_KEY, val)

    # Clear the bootinfo cache for ALL users so any manual refresh fetches
    # fresh boot data (Frappe caches frappe.boot per-user in Redis).
    try:
        frappe.cache.delete_keys("bootinfo")
    except Exception:
        frappe.clear_cache()

    # Broadcast to every connected desk session so all browsers update at once
    # without needing each user to hard-refresh.
    frappe.publish_realtime(
        event="customer_mobile_validation_flag_changed",
        message={"enabled": val == "1"},
        after_commit=True,
    )
    return {"enabled": val == "1"}


# ─── Validation ──────────────────────────────────────────────────────────────
def _validate_mobile(number, fieldname):
    if not number:
        return

    cleaned = number.strip()
    if not cleaned.startswith("+"):
        frappe.throw(
            _("Phone Number {0} in field {1} must start with a country code (e.g. +201234567890).").format(
                frappe.bold(cleaned), frappe.bold(fieldname)
            ),
            frappe.ValidationError,
        )

    try:
        from phonenumbers import NumberParseException, is_valid_number, number_type, parse
        from phonenumbers.phonenumberutil import PhoneNumberType

        try:
            parsed = parse(cleaned)
            if is_valid_number(parsed):
                if number_type(parsed) == PhoneNumberType.FIXED_LINE:
                    frappe.throw(
                        _("Phone Number {0} in field {1} is not valid (landline numbers are not allowed; please enter a mobile number).").format(
                            frappe.bold(cleaned), frappe.bold(fieldname)
                        ),
                        frappe.ValidationError,
                    )
                return
        except NumberParseException:
            pass

        frappe.throw(
            _("Phone Number {0} in field {1} is not valid.").format(
                frappe.bold(cleaned), frappe.bold(fieldname)
            ),
            frappe.ValidationError,
        )

    except ImportError:
        digits = cleaned[1:]
        if not digits.isdigit() or not (7 <= len(digits) <= 15) or digits[0] == "0":
            frappe.throw(
                _("Phone Number {0} in field {1} is not valid.").format(
                    frappe.bold(cleaned), frappe.bold(fieldname)
                ),
                frappe.ValidationError,
            )


# ─── Duplicate detection / format upgrade ────────────────────────────────────
# When a Customer is saved with a properly-formatted mobile (+CC...), look for
# any other Customer whose stored number, normalized to its national-number
# form (country code stripped, leading 0 stripped, non-digits removed),
# matches the new one. If found, that's the same person — upgrade the
# existing customer's number to the new format (when the UNIQUE index allows
# it) and refuse the current save so no duplicate Customer row is ever
# created.
#
# Country detection is done by `phonenumbers` so it works for any country
# code, not just Egypt. For raw local-format strings (e.g. "01001014012") we
# fall back to parsing with the configured default region.
_DEFAULT_REGION = "EG"


def _national_number(num):
    """Return the national-subscriber digits of `num` as a string, or None.

    Handles +CC, 00CC, or local-format inputs. Falls back to digits-only minus
    leading zeros when the phonenumbers library can't parse the value.
    """
    if not num:
        return None
    cleaned = str(num).strip()
    if not cleaned:
        return None
    try:
        from phonenumbers import NumberParseException, parse

        for candidate in (
            cleaned,
            ("+" + cleaned[2:]) if cleaned.startswith("00") else None,
        ):
            if not candidate:
                continue
            try:
                parsed = parse(candidate, None)
                return str(parsed.national_number)
            except NumberParseException:
                pass
        try:
            parsed = parse(cleaned, _DEFAULT_REGION)
            return str(parsed.national_number)
        except NumberParseException:
            pass
    except ImportError:
        pass
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    return digits.lstrip("0") or None


def _find_duplicate_customers(doc, national_number):
    """Find every other Customer whose stored mobile maps to the same national number.

    Pre-filters in SQL by stripping every non-digit from the stored value with
    REGEXP_REPLACE (so values like "010 63514451" or "0106-351-4451" still
    match), then exact-matches in Python via _national_number. Returns a list
    of dict rows; empty list when nothing matches.
    """
    if not national_number:
        return []
    safe = national_number.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{safe}"
    candidates = frappe.db.sql(
        """
        SELECT name, mobile_no, custom_mobile_intl
        FROM `tabCustomer`
        WHERE name <> %s
          AND (
              REGEXP_REPLACE(COALESCE(mobile_no, ''), '[^0-9]', '') LIKE %s
              OR REGEXP_REPLACE(COALESCE(custom_mobile_intl, ''), '[^0-9]', '') LIKE %s
          )
        LIMIT 50
        """,
        (doc.name or "__new__", pattern, pattern),
        as_dict=True,
    )
    matches = []
    for c in candidates:
        for v in (c.get("custom_mobile_intl"), c.get("mobile_no")):
            if v and _national_number(v) == national_number:
                matches.append(c)
                break
    return matches


def _check_duplicate_and_upgrade(doc):
    new_num = (doc.get("custom_mobile_intl") or doc.get("mobile_no") or "").strip()
    if not new_num or not new_num.startswith("+"):
        return
    nn = _national_number(new_num)
    if not nn:
        return
    matches = _find_duplicate_customers(doc, nn)
    if not matches:
        return

    # Is any match already in the clean +CC... format? If yes, no other dirty
    # row can be upgraded because mobile_no has a UNIQUE index — only one row
    # can hold the clean value at a time.
    clean_holder = None
    for m in matches:
        if (m.get("mobile_no") or "").strip() == new_num or (m.get("custom_mobile_intl") or "").strip() == new_num:
            clean_holder = m
            break

    if not clean_holder:
        # Schedule the format-upgrade for a background worker. We can't do
        # it inline because we're about to `frappe.throw(...)`, and
        # committing here to preserve the upgrade would also commit the
        # in-progress autoname series increment — leaving a gap in Customer
        # IDs (e.g. CUST-...-00050 followed by CUST-...-00052, skipping 51).
        # The worker runs the upgrade in its own transaction after this
        # request's rollback finishes, so the series counter rolls back
        # cleanly with no gap.
        frappe.enqueue(
            "customer_mobile_validation.customer._upgrade_customer_format",
            queue="short",
            customer_name=matches[0]["name"],
            new_num=new_num,
        )

    names = [m["name"] for m in matches]
    if len(names) == 1:
        msg = _(
            "Mobile number {0} already belongs to existing customer {1}. "
            "Please use the existing record instead."
        ).format(frappe.bold(new_num), frappe.bold(names[0]))
    else:
        msg = _(
            "Mobile number {0} already belongs to {1} existing customers: {2}. "
            "Please use one of the existing records instead."
        ).format(frappe.bold(new_num), len(names), frappe.bold(", ".join(names)))
    frappe.throw(msg, frappe.DuplicateEntryError)


def _upgrade_customer_format(customer_name, new_num):
    """Background job: bring an existing Customer's mobile to the clean
    +CC... format. Runs after the originating save has been rolled back, in
    its own transaction. Keeping the upgrade out of `validate` avoids any
    mid-request commit, which is what previously caused the Customer-ID
    series to skip numbers on duplicate-rejected saves.
    """
    if not frappe.db.exists("Customer", customer_name):
        return
    row = frappe.db.get_value(
        "Customer", customer_name, ["mobile_no", "custom_mobile_intl"], as_dict=True
    )
    if not row:
        return
    existing_mobile = (row.get("mobile_no") or "").strip()
    existing_intl = (row.get("custom_mobile_intl") or "").strip()
    if existing_mobile == new_num and existing_intl == new_num:
        return  # already upgraded

    # Re-check that no other customer owns the clean value (could have
    # happened between enqueue time and now). If so, leave this one alone —
    # the UNIQUE index on mobile_no would reject the write anyway.
    collision = frappe.db.sql(
        """SELECT name FROM `tabCustomer`
           WHERE name <> %s AND (mobile_no = %s OR custom_mobile_intl = %s)
           LIMIT 1""",
        (customer_name, new_num, new_num),
    )
    if collision:
        return

    if existing_mobile != new_num:
        frappe.db.set_value("Customer", customer_name, "mobile_no", new_num, update_modified=False)
    if existing_intl != new_num:
        frappe.db.set_value("Customer", customer_name, "custom_mobile_intl", new_num, update_modified=False)
    frappe.db.commit()


def validate_customer(doc, method):
    if not _is_enabled():
        return
    _validate_mobile(doc.get("custom_mobile_intl") or doc.get("mobile_no"), "Mobile")
    _check_duplicate_and_upgrade(doc)


# ─── Bidirectional sync ──────────────────────────────────────────────────────
def sync_customer_mobile(doc, method):
    """After save: keep custom_mobile_intl and mobile_no in sync in both directions.

    Customer.mobile_no is a Read-Only fetched field (fetch_from=customer_primary_contact.mobile_no),
    so we use db.set_value to bypass fetch_from and write the DB column directly.

    - Full form writes custom_mobile_intl -> copy into mobile_no.
    - Quick entry writes mobile_no (via mobile_number) -> copy into custom_mobile_intl.
    """
    if not _is_enabled():
        return

    intl = (doc.get("custom_mobile_intl") or "").strip()
    mobile = (doc.get("mobile_no") or "").strip()

    if intl and intl != mobile:
        frappe.db.set_value("Customer", doc.name, "mobile_no", intl, update_modified=False)
    elif mobile and not intl:
        frappe.db.set_value("Customer", doc.name, "custom_mobile_intl", mobile, update_modified=False)
