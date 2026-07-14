# Copyright (c) 2026, Exalix Tech and contributors
# For license information, please see license.txtt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today, add_to_date
import io
import base64


class DMSGatePass(Document):

	def before_insert(self):
		self._set_defaults()

	def validate(self):
		self._validate_vehicle_pass()
		self._auto_expire_old_passes()

	def on_submit(self):
		pass

	def after_insert(self):
		self._generate_qr_code()

	# ------------------------------------------------------------------
	# Private helpers
	# ------------------------------------------------------------------

	def _set_defaults(self):
		"""Set default valid_from / valid_until if not provided."""
		if not self.valid_from:
			self.valid_from = now_datetime()
		if not self.valid_until:
			# Default: pass expires end-of-day
			self.valid_until = add_to_date(self.valid_from, days=1)

	def _validate_vehicle_pass(self):
		"""Ensure no duplicate active gate pass for the same vehicle on the same date."""
		duplicate = frappe.db.get_value(
			"DMS Gate Pass",
			{
				"vehicle": self.vehicle,
				"pass_date": self.pass_date,
				"status": "Active",
				"name": ("!=", self.name),
			},
			"name",
		)
		if duplicate:
			frappe.throw(
				frappe._(
					"An active Gate Pass <b>{0}</b> already exists for vehicle <b>{1}</b> on {2}. "
					"Please revoke it before creating a new one."
				).format(duplicate, self.vehicle, self.pass_date)
			)

	def _auto_expire_old_passes(self):
		"""Auto-expire this pass if valid_until is in the past."""
		if self.valid_until and now_datetime() > frappe.utils.get_datetime(self.valid_until):
			if self.status == "Active":
				self.status = "Expired"

	def _generate_qr_code(self):
		"""Generate a QR code image embedding the gate pass details."""
		try:
			import qrcode  # bundled with Frappe/Python env

			data = (
				f"GATEPASS:{self.name}|VEH:{self.vehicle}|"
				f"DRIVER:{self.driver or ''}|DATE:{self.pass_date}|"
				f"CARD:{self.card_id or ''}"
			)
			qr_img = qrcode.make(data)
			buffer = io.BytesIO()
			qr_img.save(buffer, format="PNG")
			b64 = base64.b64encode(buffer.getvalue()).decode()
			# Save as inline base64 data URI
			frappe.db.set_value(
				"DMS Gate Pass",
				self.name,
				"qr_code",
				f"data:image/png;base64,{b64}",
			)
		except ImportError:
			frappe.log_error("qrcode package not installed — QR generation skipped", "DMS Gate Pass")
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "DMS Gate Pass QR Error")


# ======================================================================
# Whitelisted API — called by gate scanner (Android / RFID reader)
# ======================================================================

@frappe.whitelist()
def scan_gate_card(card_id, direction, odometer=None, gate_name=None):
	"""
	Called by the gate scanner app / RFID reader when a card is presented.

	Args:
		card_id   : RFID / QR UID printed on the card
		direction : "Entry" or "Exit"
		odometer  : Current odometer reading (optional)
		gate_name : Name of the gate location (optional)

	Returns:
		dict with status (ALLOWED / DENIED), gate_pass name, vehicle info
	"""
	if not card_id:
		return {"status": "DENIED", "message": "No card ID provided"}

	# Find active gate pass for this card
	gate_pass_name = frappe.db.get_value(
		"DMS Gate Pass",
		{"card_id": card_id, "status": "Active"},
		"name",
	)

	if not gate_pass_name:
		# Try by vehicle license plate (fallback — QR might encode plate)
		vehicle = frappe.db.get_value("Vehicle", {"license_plate": card_id}, "name")
		if vehicle:
			gate_pass_name = frappe.db.get_value(
				"DMS Gate Pass",
				{"vehicle": vehicle, "status": "Active", "pass_date": today()},
				"name",
			)

	if not gate_pass_name:
		frappe.log_error(
			f"Gate scan DENIED — card_id={card_id}, direction={direction}",
			"DMS Gate Pass Scan",
		)
		return {
			"status": "DENIED",
			"message": "No active Gate Pass found for this card. Vehicle cannot proceed.",
		}

	# Log the scan into the child table
	doc = frappe.get_doc("DMS Gate Pass", gate_pass_name)
	doc.append(
		"gate_logs",
		{
			"log_time": now_datetime(),
			"direction": direction,
			"scanned_by": frappe.session.user,
			"odometer_reading": flt(odometer),
			"location": gate_name or "",
		},
	)
	doc.save(ignore_permissions=True)

	# If exiting → auto-create / update the Trip Log with start odometer
	if direction == "Exit" and odometer:
		_sync_trip_log_on_exit(gate_pass_name, doc.vehicle, doc.driver, doc.van_assignment, odometer)

	# If entering → close the Trip Log with end odometer
	if direction == "Entry" and odometer:
		_sync_trip_log_on_entry(gate_pass_name, odometer)

	return {
		"status": "ALLOWED",
		"gate_pass": gate_pass_name,
		"vehicle": doc.vehicle,
		"driver": doc.driver,
		"direction": direction,
		"message": f" {direction} ALLOWED for {doc.vehicle}",
	}


def _sync_trip_log_on_exit(gate_pass, vehicle, driver, van_assignment, odometer):
	"""Create a new Trip Log when the van exits the gate."""
	from frappe.utils import flt
	existing = frappe.db.get_value(
		"DMS Vehicle Trip Log",
		{"gate_pass": gate_pass, "trip_status": "In Progress"},
		"name",
	)
	if existing:
		return  # already has an in-progress trip

	beat = frappe.db.get_value("DMS Van Assignment", van_assignment, "beat") if van_assignment else None
	trip = frappe.new_doc("DMS Vehicle Trip Log")
	trip.vehicle = vehicle
	trip.driver = driver
	trip.van_assignment = van_assignment
	trip.gate_pass = gate_pass
	trip.trip_date = today()
	trip.beat = beat
	trip.odometer_start = flt(odometer)
	trip.trip_status = "In Progress"
	trip.insert(ignore_permissions=True)


def _sync_trip_log_on_entry(gate_pass, odometer):
	"""Update Trip Log with end odometer when van returns."""
	from frappe.utils import flt
	trip_name = frappe.db.get_value(
		"DMS Vehicle Trip Log",
		{"gate_pass": gate_pass, "trip_status": "In Progress"},
		"name",
	)
	if trip_name:
		trip = frappe.get_doc("DMS Vehicle Trip Log", trip_name)
		trip.odometer_end = flt(odometer)
		trip.trip_status = "Completed"
		trip.save(ignore_permissions=True)


def flt(value):
	try:
		return float(value or 0)
	except (ValueError, TypeError):
		return 0.0
