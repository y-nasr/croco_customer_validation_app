// Toggle: every customization in this app is gated by this flag.
// When false, none of the app's customizations apply (server validation,
// dedup, server sync, quick-entry picker, and the full-form hide of
// custom_mobile_intl).
function customer_mobile_validation_enabled() {
	return !(frappe.boot && frappe.boot.customer_mobile_validation_enabled === false);
}

frappe.ui.form.on("Customer", {
	setup: function (frm) {
		// Workaround for a change introduced in Frappe v15.38.0
		if (frm.is_dialog) return;
		if (customer_mobile_validation_enabled()) {
			// Users edit mobile via the stock `mobile_no` (read-only, fetched
			// from the Primary Contact); `custom_mobile_intl` is a hidden
			// backing store kept in sync by the server.
			frm.set_df_property("custom_mobile_intl", "hidden", 1);
		}
	},
});
