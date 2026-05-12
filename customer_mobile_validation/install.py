import frappe


def after_install():
    """Create the custom_mobile_intl field on Customer if it doesn't exist.

    Customer.mobile_no is a Read-Only fetched field (fetch_from =
    customer_primary_contact.mobile_no), so it can't be typed into directly.
    We add a plain editable Data field as a backing store for the quick-entry
    picker / for the bidirectional sync.
    """
    if frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "custom_mobile_intl"}):
        return
    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Customer",
        "label": "Mobile",
        "fieldname": "custom_mobile_intl",
        "fieldtype": "Data",
        "options": "Phone",
        "insert_after": "mobile_no",
        "in_list_view": 0,
        "in_standard_filter": 0,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
