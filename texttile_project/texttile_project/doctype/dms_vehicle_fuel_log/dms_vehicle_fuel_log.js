// Copyright (c) 2026, Exalix Tech and contributors

frappe.ui.form.on('DMS Vehicle Fuel Log', {
	quantity_litres(frm) { _calc(frm); },
	rate_per_litre(frm) { _calc(frm); },
	odometer_at_fill(frm) { _calc_mileage(frm); },

	fuel_type(frm) {
		// Show a note about fuel type price — user can manually update
		if (frm.doc.fuel_type) {
			frappe.show_alert({
				message: __('Enter today\'s {0} price per litre manually, or use the fuel price lookup.', [frm.doc.fuel_type]),
				indicator: 'blue'
			}, 4);
		}
	},

	vehicle(frm) {
		// Auto-fetch driver from active van assignment
		if (frm.doc.vehicle && !frm.doc.driver) {
			frappe.db.get_value('DMS Van Assignment', {
				vehicle: frm.doc.vehicle,
				status: 'Active'
			}, 'driver', function (r) {
				if (r && r.driver) frm.set_value('driver', r.driver);
			});
		}
	}
});

function _calc(frm) {
	let cost = flt(frm.doc.quantity_litres) * flt(frm.doc.rate_per_litre);
	frm.set_value('total_fuel_cost', cost);
}

function _calc_mileage(frm) {
	let km = flt(frm.doc.odometer_at_fill) - flt(frm.doc.last_odometer);
	frm.set_value('km_since_last_fill', km > 0 ? km : 0);
	if (km > 0 && flt(frm.doc.quantity_litres) > 0) {
		frm.set_value('mileage_kmpl', km / flt(frm.doc.quantity_litres));
	}
}

function flt(v) { return parseFloat(v) || 0; }
