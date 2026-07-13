frappe.ui.form.on("WhatsApp Order Request", {
	refresh(frm) {
		if (frm.doc.status === "Pending" && frm.doc.customer && frm.doc.parsed_item) {
			frm.add_custom_button(__("Create Sales Order"), () => {
				const execute_creation = () => {
					frappe.call({
						method: "texttile_project.texttile_project.doctype.whatsapp_order_request.whatsapp_order_request.create_sales_order_from_request",
						args: {
							request_name: frm.doc.name
						},
						freeze: true,
						callback: function(r) {
							if (r.message) {
								frappe.show_alert({
									message: __("Sales Order {0} created successfully.", [r.message]),
									indicator: "green"
								});
								frappe.set_route("Form", "Sales Order", r.message);
							}
						}
					});
				};

				if (frm.is_dirty()) {
					frm.save("", () => {
						execute_creation();
					});
				} else {
					execute_creation();
				}
			});
		}
	}
});
