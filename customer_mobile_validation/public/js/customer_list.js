// Adds a "Customer Mobile Validation" toggle to the Customer list page menu.
// Visible to the Administrator user only. Reflects current state in its label
// and reloads the page after toggling so the new flag value takes effect everywhere.

frappe.listview_settings["Customer"] = frappe.listview_settings["Customer"] || {};

(function () {
	var orig_onload = frappe.listview_settings["Customer"].onload;

	frappe.listview_settings["Customer"].onload = function (listview) {
		if (orig_onload) orig_onload.call(this, listview);

		// Administrator only — even other System Managers don't see this.
		if ((frappe.session.user || "").toLowerCase() !== "administrator") return;

		var enabled = !(frappe.boot && frappe.boot.customer_mobile_validation_enabled === false);
		var label = enabled
			? __("Customer Mobile Validation: ON (click to disable)")
			: __("Customer Mobile Validation: OFF (click to enable)");

		listview.page.add_menu_item(label, function () {
			var msg = enabled
				? __("Disable Customer Mobile Validation? Quick-entry picker, server validation, and bidirectional sync will be turned off.")
				: __("Enable Customer Mobile Validation? Quick-entry picker, server validation, and bidirectional sync will be turned on.");

			frappe.confirm(msg, function () {
				// Mark this tab as the originator so the realtime listener
				// doesn't double-reload (the callback below already reloads).
				window._cmv_toggle_self = true;
				frappe.call({
					method: "customer_mobile_validation.customer.set_customer_mobile_validation_status",
					args: { enabled: enabled ? 0 : 1 },
					callback: function (r) {
						if (!r || !r.message) return;
						frappe.show_alert({
							message: __("Customer Mobile Validation is now ") + (r.message.enabled ? "ON" : "OFF"),
							indicator: r.message.enabled ? "green" : "orange",
						});
						setTimeout(function () { window.location.reload(); }, 900);
					},
				});
			});
		});
	};
})();
