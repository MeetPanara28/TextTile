# Copyright (c) 2026, Exalix Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class DMSVehicleTripLog(Document):

	def validate(self):
		self._calculate_km_driven()
		self._aggregate_toll()
		self._aggregate_fuel()
		self._aggregate_driver_expenses()
		self._calculate_totals()

	# ------------------------------------------------------------------
	# Calculations
	# ------------------------------------------------------------------

	def _calculate_km_driven(self):
		if self.odometer_end and self.odometer_start:
			self.total_km_driven = flt(self.odometer_end) - flt(self.odometer_start)
		elif self.odometer_end:
			self.total_km_driven = flt(self.odometer_end)

	def _aggregate_toll(self):
		"""Sum all toll entries in the child table."""
		self.total_toll_amount = sum(flt(row.toll_amount) for row in (self.toll_details or []))

	def _aggregate_fuel(self):
		"""Pull fuel totals from all Vehicle Fuel Logs linked to this trip."""
		if not self.name or self.is_new():
			return
		result = frappe.db.sql(
			"""
			SELECT
				COALESCE(SUM(quantity_litres), 0) AS qty,
				COALESCE(SUM(total_fuel_cost), 0) AS cost
			FROM `tabDMS Vehicle Fuel Log`
			WHERE trip_log = %s AND docstatus != 2
			""",
			self.name,
			as_dict=True,
		)
		if result:
			self.total_fuel_qty = flt(result[0].qty)
			self.total_fuel_cost = flt(result[0].cost)
			if self.total_fuel_qty and self.total_km_driven:
				self.avg_mileage = flt(self.total_km_driven) / flt(self.total_fuel_qty)

	def _aggregate_driver_expenses(self):
		"""Sum all approved Driver Expense Vouchers for this trip."""
		if not self.name or self.is_new():
			return
		result = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(amount), 0) AS total
			FROM `tabDMS Driver Expense Voucher`
			WHERE trip_log = %s AND approval_status = 'Approved' AND docstatus != 2
			""",
			self.name,
			as_dict=True,
		)
		if result:
			self.total_driver_expenses = flt(result[0].total)

	def _calculate_totals(self):
		self.total_trip_cost = (
			flt(self.total_fuel_cost)
			+ flt(self.total_toll_amount)
			+ flt(self.total_driver_expenses)
		)
		if flt(self.total_km_driven) > 0:
			self.cost_per_km = flt(self.total_trip_cost) / flt(self.total_km_driven)
