# Copyright (c) 2026, Exalix Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class DMSVehicleFuelLog(Document):

	def before_insert(self):
		self._fetch_last_odometer()

	def validate(self):
		self._calculate_cost()
		self._calculate_mileage()

	def on_save(self):
		self._update_trip_log_fuel_totals()

	# ------------------------------------------------------------------

	def _fetch_last_odometer(self):
		"""Auto-fetch previous odometer reading from latest fuel log for this vehicle."""
		last = frappe.db.sql(
			"""
			SELECT odometer_at_fill
			FROM `tabDMS Vehicle Fuel Log`
			WHERE vehicle = %s AND docstatus != 2
			ORDER BY fuel_date DESC, creation DESC
			LIMIT 1
			""",
			self.vehicle,
			as_dict=True,
		)
		if last:
			self.last_odometer = flt(last[0].odometer_at_fill)

	def _calculate_cost(self):
		self.total_fuel_cost = flt(self.quantity_litres) * flt(self.rate_per_litre)

	def _calculate_mileage(self):
		if self.odometer_at_fill and self.last_odometer:
			self.km_since_last_fill = flt(self.odometer_at_fill) - flt(self.last_odometer)
		if self.km_since_last_fill and self.quantity_litres:
			self.mileage_kmpl = flt(self.km_since_last_fill) / flt(self.quantity_litres)

	def _update_trip_log_fuel_totals(self):
		"""Trigger Trip Log recalculation whenever a fuel log is saved."""
		if self.trip_log:
			try:
				trip = frappe.get_doc("DMS Vehicle Trip Log", self.trip_log)
				trip.save(ignore_permissions=True)
			except Exception:
				pass
