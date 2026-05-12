app_name = "customer_mobile_validation"
app_title = "Customer Mobile Validation"
app_publisher = "Your Company"
app_description = "Validates and normalizes Customer mobile numbers (E.164, +CC...) with cross-Customer duplicate detection and on-save format upgrade."
app_email = "you@example.com"
app_license = "MIT"


# ── Asset cache-busting ──────────────────────────────────────────────────────
# nginx serves /assets/<app>/js/*.js with `Cache-Control: max-age=1y`, so
# browsers hold the old file forever. Append a query string based on the
# file's mtime — when we edit the file and `bench restart` runs, hooks.py is
# re-imported, the new mtime is picked up, the URL changes, and every browser
# re-fetches the file automatically.
import os as _os
_PUBLIC = _os.path.join(_os.path.dirname(__file__), "public")
def _v(rel):
    try:
        return f"/assets/customer_mobile_validation/{rel}?v={int(_os.path.getmtime(_os.path.join(_PUBLIC, rel)))}"
    except OSError:
        return f"/assets/customer_mobile_validation/{rel}"


app_include_js = [
    _v("js/customer_quick_entry_patch.js"),
    _v("js/customer_mobile_flag_listener.js"),
]

doctype_js = {
    "Customer": "public/js/customer.js",
}

doctype_list_js = {
    "Customer": "public/js/customer_list.js",
}

doc_events = {
    "Customer": {
        "validate": "customer_mobile_validation.customer.validate_customer",
        "on_update": "customer_mobile_validation.customer.sync_customer_mobile",
        "after_insert": "customer_mobile_validation.customer.sync_customer_mobile",
    },
}

# Expose the feature flag to the desk so JS can gate its logic.
boot_session = "customer_mobile_validation.customer.boot_customer_mobile"

# Create the `custom_mobile_intl` field on Customer when the app is installed.
after_install = "customer_mobile_validation.install.after_install"
