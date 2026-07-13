# Copyright (c) 2026, Exalix Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class DMSDriverExpenseVoucher(Document):

	def validate(self):
		self._validate_amount()

	def on_save(self):
		self._update_trip_log_expense_totals()

	def on_update_after_submit(self):
		"""If approval status changes, update the trip log totals."""
		self._update_trip_log_expense_totals()

	# ------------------------------------------------------------------

	def _validate_amount(self):
		if self.amount and self.amount <= 0:
			frappe.throw(frappe._("Amount must be greater than zero."))

	def _update_trip_log_expense_totals(self):
		"""Re-trigger Trip Log recalculation when expense is approved/rejected."""
		if self.trip_log:
			try:
				trip = frappe.get_doc("DMS Vehicle Trip Log", self.trip_log)
				trip.save(ignore_permissions=True)
			except Exception:
				pass


# ------------------------------------------------------------------
# Whitelisted API — approve / reject from UI
# ------------------------------------------------------------------

@frappe.whitelist()
def approve_expense(voucher_name):
	doc = frappe.get_doc("DMS Driver Expense Voucher", voucher_name)
	doc.approval_status = "Approved"
	doc.approved_by = frappe.session.user
	doc.save(ignore_permissions=True)
	frappe.msgprint(frappe._("Expense voucher <b>{0}</b> has been Approved.").format(voucher_name))


@frappe.whitelist()
def reject_expense(voucher_name, reason=None):
	doc = frappe.get_doc("DMS Driver Expense Voucher", voucher_name)
	doc.approval_status = "Rejected"
	doc.approved_by = frappe.session.user
	if reason:
		doc.remarks = (doc.remarks or "") + f"\n[Rejected] {reason}"
	doc.save(ignore_permissions=True)
	frappe.msgprint(frappe._("Expense voucher <b>{0}</b> has been Rejected.").format(voucher_name))
