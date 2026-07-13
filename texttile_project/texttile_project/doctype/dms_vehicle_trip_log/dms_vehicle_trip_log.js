// Copyright (c) 2026, Exalix Tech and contributors

frappe.ui.form.on('DMS Vehicle Trip Log', {
	refresh(frm) {
		frm.page.set_indicator(frm.doc.trip_status, {
			'In Progress': 'blue',
			'Completed': 'green',
			'Cancelled': 'red'
		}[frm.doc.trip_status] || 'grey');

		if (!frm.is_new()) {
			// Quick link to create Fuel Log
			frm.add_custom_button(__('Add Fuel Log'), function () {
				frappe.new_doc('DMS Vehicle Fuel Log', {
					trip_log: frm.doc.name,
					vehicle: frm.doc.vehicle,
					driver: frm.doc.driver,
					gate_pass: frm.doc.gate_pass,
					fuel_date: frm.doc.trip_date
				});
			}, __('Create'));

			// Quick link to create Expense Voucher
			frm.add_custom_button(__('Add Driver Expense'), function () {
				frappe.new_doc('DMS Driver Expense Voucher', {
					trip_log: frm.doc.name,
					vehicle: frm.doc.vehicle,
					driver: frm.doc.driver,
					gate_pass: frm.doc.gate_pass,
					expense_date: frm.doc.trip_date
				});
			}, __('Create'));

			// Recalculate totals manually
			frm.add_custom_button(__('Recalculate Totals'), function () {
				frm.save().then(() => {
					frappe.show_alert({ message: 'Totals recalculated!', indicator: 'green' });
					frm.reload_doc();
				});
			});
		}
	},

	odometer_start(frm) { _calc_km(frm); },
	odometer_end(frm) { _calc_km(frm); }
});

frappe.ui.form.on('DMS Toll Entry', {
	toll_amount(frm) { _sum_tolls(frm); },
	toll_details_remove(frm) { _sum_tolls(frm); }
});

function _calc_km(frm) {
	let km = flt(frm.doc.odometer_end) - flt(frm.doc.odometer_start);
	frm.set_value('total_km_driven', km > 0 ? km : 0);
}

function _sum_tolls(frm) {
	let total = 0;
	(frm.doc.toll_details || []).forEach(row => { total += flt(row.toll_amount); });
	frm.set_value('total_toll_amount', total);
}

function flt(v) { return parseFloat(v) || 0; }
