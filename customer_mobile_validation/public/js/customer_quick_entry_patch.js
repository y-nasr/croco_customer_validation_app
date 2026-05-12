window.PHONE_COUNTRIES = [
	{ name: "Egypt",                iso: "eg", dial: "+20",  example: "1098234567"  },
	{ name: "Saudi Arabia",         iso: "sa", dial: "+966", example: "501234567"   },
	{ name: "United Arab Emirates", iso: "ae", dial: "+971", example: "501234567"   },
	{ name: "Kuwait",               iso: "kw", dial: "+965", example: "51234567"    },
	{ name: "Qatar",                iso: "qa", dial: "+974", example: "33123456"    },
	{ name: "Bahrain",              iso: "bh", dial: "+973", example: "36123456"    },
	{ name: "Oman",                 iso: "om", dial: "+968", example: "91234567"    },
	{ name: "Jordan",               iso: "jo", dial: "+962", example: "791234567"   },
	{ name: "Lebanon",              iso: "lb", dial: "+961", example: "71123456"    },
	{ name: "Iraq",                 iso: "iq", dial: "+964", example: "7901234567"  },
	{ name: "Syria",                iso: "sy", dial: "+963", example: "944567890"   },
	{ name: "Libya",                iso: "ly", dial: "+218", example: "911234567"   },
	{ name: "Tunisia",              iso: "tn", dial: "+216", example: "21234567"    },
	{ name: "Algeria",              iso: "dz", dial: "+213", example: "551234567"   },
	{ name: "Morocco",              iso: "ma", dial: "+212", example: "612345678"   },
	{ name: "Sudan",                iso: "sd", dial: "+249", example: "911234567"   },
	{ name: "Yemen",                iso: "ye", dial: "+967", example: "711234567"   },
	{ name: "Palestine",            iso: "ps", dial: "+970", example: "599123456"   },
	{ name: "United Kingdom",       iso: "gb", dial: "+44",  example: "7400123456"  },
	{ name: "United States",        iso: "us", dial: "+1",   example: "2025550143"  },
	{ name: "Canada",               iso: "ca", dial: "+1",   example: "4165550143"  },
	{ name: "France",               iso: "fr", dial: "+33",  example: "612345678"   },
	{ name: "Germany",              iso: "de", dial: "+49",  example: "15123456789" },
	{ name: "Italy",                iso: "it", dial: "+39",  example: "3123456789"  },
	{ name: "Spain",                iso: "es", dial: "+34",  example: "612345678"   },
	{ name: "Turkey",               iso: "tr", dial: "+90",  example: "5321234567"  },
	{ name: "India",                iso: "in", dial: "+91",  example: "9876543210"  },
	{ name: "Pakistan",             iso: "pk", dial: "+92",  example: "3001234567"  },
	{ name: "Bangladesh",           iso: "bd", dial: "+880", example: "1712345678"  },
	{ name: "Nigeria",              iso: "ng", dial: "+234", example: "8031234567"  },
	{ name: "South Africa",         iso: "za", dial: "+27",  example: "711234567"   },
	{ name: "Kenya",                iso: "ke", dial: "+254", example: "712345678"   },
	{ name: "Ghana",                iso: "gh", dial: "+233", example: "244123456"   },
	{ name: "China",                iso: "cn", dial: "+86",  example: "13123456789" },
	{ name: "Japan",                iso: "jp", dial: "+81",  example: "9012345678"  },
	{ name: "Australia",            iso: "au", dial: "+61",  example: "412345678"   },
	{ name: "Russia",               iso: "ru", dial: "+7",   example: "9123456789"  },
	{ name: "Brazil",               iso: "br", dial: "+55",  example: "11912345678" },
];

var COUNTRY_SELECT_OPTIONS = PHONE_COUNTRIES.map(function (c) {
	return c.name + " (" + c.dial + ")";
}).join("\n");

var OPTION_TO_DIAL = {};
var OPTION_TO_EXAMPLE = {};
PHONE_COUNTRIES.forEach(function (c) {
	var key = c.name + " (" + c.dial + ")";
	OPTION_TO_DIAL[key]    = c.dial;
	OPTION_TO_EXAMPLE[key] = c.example;
});

function apply_customer_quick_entry_patch() {
	var Base = frappe.ui && frappe.ui.form && frappe.ui.form.CustomerQuickEntryForm;
	if (!Base || Base._cmv_patched) return;

	frappe.ui.form.CustomerQuickEntryForm = class extends Base {
		get_variant_fields() {
			var fields = super.get_variant_fields().filter(function (f) {
				// Hide email from the quick-entry dialog — only the mobile flow is needed here.
				// (ERPNext labels this field "Email Id" but its actual fieldname is "email_address".)
				return f.fieldname !== "email_address";
			});
			return fields.map(function (f) {
				if (f.fieldname === "mobile_number") {
					return [
						{
							label: __("Country Code"),
							fieldname: "ph_country_code",
							fieldtype: "Select",
							options: COUNTRY_SELECT_OPTIONS,
							default: "Egypt (+20)",
						},
						{
							label: __("Mobile Number"),
							fieldname: "mobile_number",
							fieldtype: "Data",
							placeholder: "e.g. " + OPTION_TO_EXAMPLE["Egypt (+20)"],
							reqd: 1,
						},
					];
				}
				return f;
			}).reduce(function (acc, val) { return acc.concat(val); }, []);
		}

		render_dialog() {
			super.render_dialog();
			var dialog = this.dialog;
			if (!dialog) return;
			var country_field = dialog.fields_dict["ph_country_code"];
			var mobile_field  = dialog.fields_dict["mobile_number"];
			if (!country_field || !mobile_field || !mobile_field.$input) return;

			mobile_field.$input.attr("id", "mobile_number");

			function update_placeholder() {
				var selected = dialog.get_value("ph_country_code") || "Egypt (+20)";
				var example  = OPTION_TO_EXAMPLE[selected] || "1234567890";
				mobile_field.$input.attr("placeholder", "e.g. " + example);
			}

			country_field.$input.on("change", update_placeholder);
			update_placeholder();
		}

		_combined_mobile() {
			var dialog = this.dialog;
			var selected = dialog.doc["ph_country_code"] || dialog.get_value("ph_country_code") || "Egypt (+20)";
			var dial = OPTION_TO_DIAL[selected] || "+20";
			var dialDigits = dial.replace(/[^\d]/g, "");
			var field = dialog.fields_dict["mobile_number"];
			var raw = (field ? (field.$input.val() || "") : (dialog.get_value("mobile_number") || "")).trim();
			if (!raw) return "";

			// If the user typed their own country code (+CC or 00CC), respect it
			// and don't double-prepend the picker's dial code.
			var hasPlus = raw.charAt(0) === "+";
			var has00   = !hasPlus && raw.slice(0, 2) === "00";
			if (hasPlus || has00) {
				var digits = raw.replace(/[^\d]/g, "");
				if (has00) digits = digits.slice(2); // drop the leading 00
				// If the typed country code matches the picker, strip any trunk 0(s)
				// the user wrote between the CC and their local number.
				if (dialDigits && digits.indexOf(dialDigits) === 0) {
					var rest = digits.slice(dialDigits.length).replace(/^0+/, "");
					return rest ? "+" + dialDigits + rest : "";
				}
				return digits ? "+" + digits : "";
			}

			// Plain local number → strip leading zero(s) (national trunk prefix)
			// and prepend the picker's dial code.
			var local = raw.replace(/[^\d]/g, "").replace(/^0+/, "");
			return local ? dial + local : "";
		}

		insert() {
			var combined = this._combined_mobile();
			if (combined) this.dialog.doc["mobile_number"] = combined;
			return super.insert();
		}

		update_doc() {
			super.update_doc();
			var combined = this._combined_mobile();
			if (combined) this.dialog.doc["mobile_number"] = combined;
			delete this.dialog.doc["ph_country_code"];
			return this.dialog.doc;
		}
	};
	frappe.ui.form.CustomerQuickEntryForm._cmv_patched = true;
}

// Toggle: site_config.json -> "customer_mobile_validation_enabled": 0 disables this whole patch.
function _customer_mobile_validation_enabled() {
	return !(frappe.boot && frappe.boot.customer_mobile_validation_enabled === false);
}

// Intercept make_quick_entry so the patch is applied on demand,
// even before the Customer doctype JS has loaded.
frappe.after_ajax(function () {
	if (!_customer_mobile_validation_enabled()) return;
	var _orig = frappe.ui.form.make_quick_entry;
	frappe.ui.form.make_quick_entry = function (doctype) {
		if (doctype === "Customer") apply_customer_quick_entry_patch();
		return _orig.apply(this, arguments);
	};
});
