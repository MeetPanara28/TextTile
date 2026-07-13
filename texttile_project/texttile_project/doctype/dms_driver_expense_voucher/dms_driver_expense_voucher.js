// Copyright (c) 2026, Exalix Tech and contributors

frappe.ui.form.on('DMS Driver Expense Voucher', {
	refresh(frm) {
		frm.page.set_indicator(frm.doc.approval_status, {
			'Pending': 'orange',
			'Approved': 'green',
			'Rejected': 'red'
		}[frm.doc.approval_status] || 'grey');

		// Approve / Reject buttons (only for managers)
		if (!frm.is_new() && frm.doc.approval_status === 'Pending') {
			if (frappe.user.has_role(['System Manager', 'DMS Manager'])) {
				frm.add_custom_button(__(' Approve'), function () {
					frappe.call({
						method: 'exalix_dms.exalix_dms.doctype.dms_driver_expense_voucher.dms_driver_expense_voucher.approve_expense',
						args: { voucher_name: frm.doc.name },
						callback() { frm.reload_doc(); }
					});
				}).addClass('btn-success');

				frm.add_custom_button(__('Reject'), function () {
					frappe.prompt(
						[{ fieldname: 'reason', fieldtype: 'Small Text', label: 'Reason for rejection' }],
						function (values) {
							frappe.call({
								method: 'exalix_dms.exalix_dms.doctype.dms_driver_expense_voucher.dms_driver_expense_voucher.reject_expense',
								args: { voucher_name: frm.doc.name, reason: values.reason },
								callback() { frm.reload_doc(); }
							});
						},
						__('Reject Expense'),
						__('Confirm Rejection')
					);
				}).addClass('btn-danger');
			}
		}
	},

	driver(frm) {
		// Auto-fill vehicle from van assignment
		if (frm.doc.driver && !frm.doc.vehicle) {
			frappe.db.get_value('DMS Van Assignment', {
				driver: frm.doc.driver,
				status: 'Active'
			}, 'vehicle', function (r) {
				if (r && r.vehicle) frm.set_value('vehicle', r.vehicle);
			});
		}
	}
});
