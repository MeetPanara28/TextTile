// Copyright (c) 2026, Exalix Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on('DMS Gate Pass', {
	refresh(frm) {
		frm.page.set_indicator(frm.doc.status, {
			'Active': 'green',
			'Expired': 'orange',
			'Revoked': 'red'
		}[frm.doc.status] || 'grey');

		// Show QR code in a nice dialog
		if (!frm.is_new() && frm.doc.qr_code) {
			frm.add_custom_button(__('View QR Code'), function () {
				let d = new frappe.ui.Dialog({
					title: __('Gate Pass QR Code — {0}', [frm.doc.vehicle]),
					fields: [],
				});
				d.$body.html(`
					<div style="text-align:center; padding:20px;">
						<img src="${frm.doc.qr_code}" style="max-width:280px; border:4px solid #ddd; border-radius:8px;" />
						<p style="margin-top:12px; font-size:13px; color:#555;">
							Scan this code at the gate scanner or print on the pass slip.
						</p>
						<button class="btn btn-primary btn-sm" onclick="window.print()">Print</button>
					</div>
				`);
				d.show();
			}, __('Actions'));
		}

		// Quick Revoke button
		if (!frm.is_new() && frm.doc.status === 'Active') {
			frm.add_custom_button(__('Revoke Pass'), function () {
				frappe.confirm(
					__('Are you sure you want to revoke Gate Pass <b>{0}</b>?', [frm.doc.name]),
					function () {
						frm.set_value('status', 'Revoked');
						frm.save();
					}
				);
			}, __('Actions'));
		}

		// Manual scan simulation (for testing without hardware)
		if (!frm.is_new() && frm.doc.status === 'Active') {
			frm.add_custom_button(__('Simulate Scan'), function () {
				let d = new frappe.ui.Dialog({
					title: __('Simulate Gate Scan'),
					fields: [
						{
							fieldname: 'direction',
							fieldtype: 'Select',
							label: 'Direction',
							options: 'Exit\nEntry',
							reqd: 1,
							default: 'Exit'
						},
						{
							fieldname: 'odometer',
							fieldtype: 'Float',
							label: 'Odometer Reading (KM)',
							reqd: 1
						},
						{
							fieldname: 'gate_name',
							fieldtype: 'Data',
							label: 'Gate Name',
							default: 'Main Gate'
						}
					],
					primary_action_label: __('Scan'),
					primary_action(values) {
						frappe.call({
							method: 'exalix_dms.exalix_dms.doctype.dms_gate_pass.dms_gate_pass.scan_gate_card',
							args: {
								card_id: frm.doc.card_id || frm.doc.vehicle,
								direction: values.direction,
								odometer: values.odometer,
								gate_name: values.gate_name
							},
							callback(r) {
								d.hide();
								if (r.message && r.message.status === 'ALLOWED') {
									frappe.msgprint({
										title: __('Scan Result'),
										message: r.message.message,
										indicator: 'green'
									});
									frm.reload_doc();
								} else {
									frappe.msgprint({
										title: __('Scan Denied'),
										message: (r.message && r.message.message) || 'Access denied.',
										indicator: 'red'
									});
								}
							}
						});
					}
				});
				d.show();
			}, __('Actions'));
		}
	},

	vehicle(frm) {
		// Auto-fetch today's active Van Assignment for this vehicle
		if (frm.doc.vehicle) {
			frappe.db.get_value('DMS Van Assignment', {
				vehicle: frm.doc.vehicle,
				status: 'Active',
				assignment_date: frappe.datetime.get_today()
			}, ['name', 'driver', 'beat'], function (r) {
				if (r && r.name) {
					frm.set_value('van_assignment', r.name);
					if (!frm.doc.driver && r.driver) {
						frm.set_value('driver', r.driver);
					}
				}
			});
		}
	},

	pass_date(frm) {
		// Set valid_from to start of day, valid_until to end of day
		if (frm.doc.pass_date) {
			frm.set_value('valid_from', frm.doc.pass_date + ' 06:00:00');
			frm.set_value('valid_until', frm.doc.pass_date + ' 22:00:00');
		}
	}
});
