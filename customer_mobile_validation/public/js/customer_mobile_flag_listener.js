// Listens for the realtime broadcast emitted when the Administrator toggles
// the Customer Mobile Validation flag. Forces every connected desk session
// to reload so the new flag state takes effect everywhere immediately —
// no per-browser refresh required.

frappe.after_ajax(function () {
	if (!frappe.realtime || typeof frappe.realtime.on !== "function") return;

	frappe.realtime.on("customer_mobile_validation_flag_changed", function (data) {
		if (!data) return;
		var enabled = !!data.enabled;
		// Keep frappe.boot in sync immediately so any code reading the flag
		// before the reload completes gets the new value.
		if (frappe.boot) frappe.boot.customer_mobile_validation_enabled = enabled;

		// Don't notify or reload on the originating tab — the toggle handler
		// already shows its own alert + reload. Only act on OTHER sessions.
		if (window._cmv_toggle_self) {
			window._cmv_toggle_self = false;
			return;
		}

		frappe.show_alert({
			message: __("Customer Mobile Validation has been ") +
				(enabled ? __("enabled") : __("disabled")) +
				__(" by the Administrator. Reloading…"),
			indicator: enabled ? "green" : "orange",
		}, 6);

		// Reload every connected desk tab so the new flag state takes effect
		// everywhere. Slight delay so the toast is visible.
		setTimeout(function () { window.location.reload(); }, 1500);
	});
});
