import frappe
import re
import requests
from frappe import _

def validate_customer_whatsapp(doc, method=None):
	# Copy mobile_no if whatsapp number is missing
	if not doc.get("custom_whatsapp_number") and doc.get("mobile_no"):
		doc.custom_whatsapp_number = doc.mobile_no
		
	if doc.get("custom_whatsapp_number"):
		# Clean the number (remove spaces, dashes, parentheses)
		cleaned = re.sub(r"[\s\-\(\)]", "", doc.custom_whatsapp_number)
		
		if not cleaned.startswith("+"):
			frappe.throw(_("WhatsApp number must start with '+' followed by country code (e.g., +919876543210)."))
			
		if not re.match(r"^\+[1-9]\d{9,14}$", cleaned):
			frappe.throw(_("Invalid WhatsApp number format. Please use E.164 format (e.g. +919876543210)."))
			
		doc.custom_whatsapp_number = cleaned


def send_welcome_whatsapp(doc, method=None):
	if not doc.get("custom_whatsapp_opt_in") or not doc.get("custom_whatsapp_number"):
		return
		
	# Fetch Twilio credentials
	try:
		twilio_settings = frappe.get_doc("Twilio Settings")
		account_sid = twilio_settings.account_sid
		auth_token = twilio_settings.get_password("auth_token")
		sender_number = twilio_settings.sender_number
	except Exception:
		account_sid = None
		auth_token = None
		sender_number = None
	
	recipient_number = doc.custom_whatsapp_number
	message_body = f"Hello {doc.customer_name}, welcome to our service!"
	
	# Create log record
	log = frappe.get_doc({
		"doctype": "Twilio Message Log",
		"customer": doc.name,
		"sender": sender_number or "Unknown",
		"recipient": recipient_number,
		"message": message_body,
		"status": "Pending"
	})
	log.insert(ignore_permissions=True)
	frappe.db.commit()
	
	if not account_sid or not auth_token or not sender_number:
		log.status = "Failed"
		log.error_message = "Missing Twilio credentials in Twilio Settings."
		log.save(ignore_permissions=True)
		frappe.db.commit()
		return

	# Perform request
	try:
		# Format numbers for Twilio WhatsApp (if they don't already have whatsapp: prefix)
		from_number = sender_number if sender_number.startswith("whatsapp:") else f"whatsapp:{sender_number}"
		to_number = recipient_number if recipient_number.startswith("whatsapp:") else f"whatsapp:{recipient_number}"
		
		# Dry-run or Mock check to prevent actual credits usage
		if account_sid.startswith("mock_") or auth_token.startswith("mock_") or "ACmock" in account_sid:
			log.status = "Sent"
			log.message_sid = "SMmock1234567890"
			log.error_message = "Mock send success (Dry-Run mode)."
			log.save(ignore_permissions=True)
			frappe.db.commit()
			return
			
		url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
		payload = {
			"From": from_number,
			"To": to_number,
			"Body": message_body
		}
		
		response = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=10)
		
		if response.status_code in [200, 201]:
			res_data = response.json()
			log.status = "Sent"
			log.message_sid = res_data.get("sid")
		else:
			log.status = "Failed"
			try:
				res_data = response.json()
				log.error_message = f"Twilio Error {res_data.get('code')}: {res_data.get('message')}"
			except Exception:
				log.error_message = f"HTTP Error {response.status_code}: {response.text}"
	except Exception as e:
		log.status = "Failed"
		log.error_message = str(e)
		
	log.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def handle_twilio_webhook():
	data = frappe.form_dict
	
	sender = data.get("From")
	recipient = data.get("To")
	body = data.get("Body")
	message_sid = data.get("MessageSid")
	
	if not sender or not body:
		return "Missing parameters"
		
	# Clean sender number
	clean_phone = sender
	if clean_phone.startswith("whatsapp:"):
		clean_phone = clean_phone.replace("whatsapp:", "")
		
	# Find matching customer
	customer = frappe.db.get_value("Customer", {"custom_whatsapp_number": clean_phone}, "name")
	
	if not customer:
		# Fallback to mobile_no
		cleaned_digits = re.sub(r"\D", "", clean_phone)
		customers = frappe.db.get_all("Customer", fields=["name", "mobile_no"])
		for cust in customers:
			if cust.mobile_no and re.sub(r"\D", "", cust.mobile_no) == cleaned_digits:
				customer = cust.name
				break
				
	customer_name = frappe.db.get_value("Customer", customer, "customer_name") if customer else None
	
	# Parse item and quantity
	parsed_item = ""
	parsed_qty = 1.0
	
	# 1. Try Labeled: item: <item>, qty: <qty>
	labeled_match = re.search(r"item:\s*([^,]+)(?:,\s*|\s+)qty:\s*([\d\.]+)", body, re.IGNORECASE)
	if labeled_match:
		parsed_item = labeled_match.group(1).strip()
		try:
			parsed_qty = float(labeled_match.group(2))
		except ValueError:
			parsed_qty = 1.0
	else:
		# 2. Try comma-separated: <item>, <qty>
		comma_parts = body.split(",")
		if len(comma_parts) >= 2:
			try:
				parsed_qty = float(comma_parts[-1].strip())
				parsed_item = ",".join(comma_parts[:-1]).strip()
			except ValueError:
				parsed_item = body.strip()
		else:
			# 3. Try space-separated: <item> <qty> (where qty is last word)
			space_parts = body.strip().split()
			if len(space_parts) >= 2:
				try:
					parsed_qty = float(space_parts[-1])
					parsed_item = " ".join(space_parts[:-1]).strip()
				except ValueError:
					parsed_item = body.strip()
			else:
				parsed_item = body.strip()
				
	# Resolve parsed_item string to a valid Item Code (since parsed_item is a Link field)
	matched_item = None
	if parsed_item:
		if frappe.db.exists("Item", parsed_item):
			matched_item = parsed_item
		else:
			# Try case-insensitive item_name match
			matches = frappe.db.get_all("Item", filters={"item_name": ["like", f"%{parsed_item}%"]}, fields=["item_code"])
			if matches:
				matched_item = matches[0].item_code
			else:
				# Try case-insensitive item_code match
				matches_code = frappe.db.get_all("Item", filters={"item_code": ["like", f"%{parsed_item}%"]}, fields=["item_code"])
				if matches_code:
					matched_item = matches_code[0].item_code

	# Create WhatsApp Order Request doc
	req_doc = frappe.get_doc({
		"doctype": "WhatsApp Order Request",
		"customer": customer,
		"customer_name": customer_name,
		"whatsapp_number": clean_phone,
		"message": body,
		"parsed_item": matched_item,
		"parsed_qty": parsed_qty,
		"status": "Pending"
	})
	
	req_doc.insert(ignore_permissions=True)
	frappe.db.commit()
	
	frappe.response["type"] = "download"
	frappe.response["content_type"] = "text/xml"
	frappe.response["filename"] = "response.xml"
	frappe.response["filecontent"] = "<Response></Response>"


@frappe.whitelist(allow_guest=True)
def debug_create_sales_order():
	try:
		pending = frappe.get_all("WhatsApp Order Request", filters={"status": "Pending"}, fields=["name", "customer", "parsed_item", "parsed_qty"])
		if not pending:
			return {
				"status": "error",
				"message": "No pending WhatsApp Order Requests found.",
				"all_requests": frappe.get_all("WhatsApp Order Request", limit=10, fields=["name", "customer", "parsed_item", "status"])
			}
		
		req_name = pending[0].name
		from texttile_project.texttile_project.doctype.whatsapp_order_request.whatsapp_order_request import create_sales_order_from_request
		so_name = create_sales_order_from_request(req_name)
		return {
			"status": "success",
			"message": f"Successfully created Sales Order: {so_name} for request {req_name}"
		}
	except Exception as e:
		import traceback
		return {
			"status": "error",
			"message": str(e),
			"traceback": traceback.format_exc()
		}

def ensure_quality_inspections(ref_doc):
	"""
	Automatically creates, submits, and links a Quality Inspection
	for any item in the reference document that requires it.
	"""
	import frappe
	from frappe.utils import today
	updated = False
	for row in ref_doc.get("items", []):
		if row.get("quality_inspection"):
			continue
		item_code = row.get("item_code")
		if not item_code:
			continue
		
		# Check if Quality Inspection is required before receipt
		qi_req_receipt = frappe.db.get_value("Item", item_code, "inspection_required_before_purchase")
		if bool(qi_req_receipt):
			qi = frappe.new_doc("Quality Inspection")
			qi.naming_series = "MAT-QA-.YYYY.-"
			qi.company = ref_doc.company
			qi.report_date = ref_doc.get("posting_date") or today()
			qi.status = "Accepted"
			qi.inspection_type = "Incoming"
			qi.reference_type = ref_doc.doctype
			qi.reference_name = ref_doc.name
			qi.item_code = item_code
			qi.sample_size = row.get("qty") or 1.0
			qi.inspected_by = frappe.session.user or "Administrator"
			
			qi_template = frappe.db.get_value("Item", item_code, "quality_inspection_template")
			if qi_template:
				qi.quality_inspection_template = qi_template
				qi.get_item_specification_details()
				for reading in qi.readings:
					reading.status = "Accepted"
			
			qi.insert(ignore_permissions=True)
			qi.submit()
			
			row.quality_inspection = qi.name
			frappe.db.set_value(row.doctype, row.name, "quality_inspection", qi.name)
			updated = True
			
	if updated:
		ref_doc.reload()


def gate_pass_on_submit(doc, method=None):
	"""
	Triggered when a Gate Pass is submitted (i.e. Manager approved it).
	Automatically submits the linked Stock Entry or Subcontracting Receipt
	so the user does NOT need to manually submit it.
	"""
	ref_doctype = doc.get("reference_doctype")
	ref_name = doc.get("reference_name")

	if not ref_doctype or not ref_name:
		frappe.log_error(
			f"Gate Pass {doc.name} submitted but has no reference_doctype/reference_name linked.",
			"Gate Pass Auto Submit"
		)
		return

	try:
		ref_doc = frappe.get_doc(ref_doctype, ref_name)

		# Only submit if it is still in Draft (docstatus = 0)
		if ref_doc.docstatus == 0:
			ensure_quality_inspections(ref_doc)
			ref_doc.submit()
			frappe.msgprint(
				f"{ref_doctype} <b>{ref_name}</b> has been automatically submitted after Gate Pass approval.",
				indicator="green",
				alert=True
			)
		elif ref_doc.docstatus == 1:
			# Already submitted — nothing to do
			frappe.msgprint(
				f"{ref_doctype} <b>{ref_name}</b> is already submitted.",
				indicator="blue",
				alert=True
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Gate Pass Auto Submit Failed — {ref_name}")
		frappe.throw(
			f"Gate Pass approved, but failed to auto-submit {ref_doctype} <b>{ref_name}</b>. "
			f"Please submit it manually. Error logged.",
			title="Auto Submit Failed"
		)


@frappe.whitelist()
def filter_supplied_items_before_submit(doc, method=None):
	"""
	Hook to filter out non-stock items from supplied_items table before submission
	to prevent SLE validation errors.
	"""
	if doc.get("supplied_items"):
		stock_items_only = []
		for item in doc.get("supplied_items"):
			is_stock = frappe.db.get_value("Item", item.rm_item_code, "is_stock_item")
			if is_stock:
				stock_items_only.append(item)
			else:
				child_dt = item.doctype
				frappe.db.delete(child_dt, {"name": item.name})
		doc.set("supplied_items", stock_items_only)



@frappe.whitelist()
def create_gate_pass_from_stock_entry(stock_entry):
	"""
	Automatically creates a 'Gate Pass' document from a 'Stock Entry' (Draft).
	Maps items, company, date, and sets reference.
	Returns the name of the created Gate Pass.
	"""
	if not stock_entry:
		frappe.throw(_("Stock Entry name is required."))

	se_doc = frappe.get_doc("Stock Entry", stock_entry)

	# Check if Gate Pass already exists for this Stock Entry
	existing_gp = frappe.db.get_value(
		"Gate Pass",
		{"reference_doctype": "Stock Entry", "reference_name": stock_entry, "docstatus": ["!=", 2]},
		"name"
	)
	if existing_gp:
		# Update reference on Stock Entry just in case it wasn't linked properly
		if not se_doc.custom_gate_pass:
			se_doc.db_set("custom_gate_pass", existing_gp)
		return {"gate_pass": existing_gp}

	# Create new Gate Pass
	gp_doc = frappe.new_doc("Gate Pass")
	gp_doc.gate_pass_type = "Outward"
	gp_doc.transaction_date = se_doc.posting_date
	gp_doc.company = se_doc.company
	gp_doc.reference_doctype = "Stock Entry"
	gp_doc.reference_name = stock_entry

	# Find subcontractor/supplier from Stock Entry if applicable
	subcontractor = se_doc.get("supplier") or se_doc.get("subcontractor")
	if not subcontractor:
		if se_doc.get("purchase_order"):
			subcontractor = frappe.db.get_value("Purchase Order", se_doc.purchase_order, "supplier")
		elif se_doc.get("subcontracting_order"):
			subcontractor = frappe.db.get_value("Subcontracting Order", se_doc.subcontracting_order, "supplier")
		elif se_doc.get("subcontracting_receipt"):
			subcontractor = frappe.db.get_value("Subcontracting Receipt", se_doc.subcontracting_receipt, "supplier")

	if not subcontractor:
		frappe.throw(
			_("Could not identify the Subcontractor / Supplier for this Stock Entry. Please ensure the Supplier field is set on the Stock Entry."),
			title="Subcontractor Missing"
		)

	gp_doc.subcontractor = subcontractor

	# Add items
	for item in se_doc.items:
		gp_doc.append("items", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"qty": item.qty,
			"uom": item.stock_uom or item.uom,
			"rate": item.basic_rate or 0,
			"amount": item.amount or 0
		})

	gp_doc.insert(ignore_permissions=True)
	
	# Update link in Stock Entry
	se_doc.db_set("custom_gate_pass", gp_doc.name)

	return {"gate_pass": gp_doc.name}


@frappe.whitelist()
def create_subcontract_inward_flow(subcontracting_receipt):
	"""
	Automatically creates an Inward 'Gate Pass' document from a 'Subcontracting Receipt' (Draft).
	"""
	if not subcontracting_receipt:
		frappe.throw(_("Subcontracting Receipt name is required."))

	scr_doc = frappe.get_doc("Subcontracting Receipt", subcontracting_receipt)

	# Check if Gate Pass already exists
	existing_gp = frappe.db.get_value(
		"Gate Pass",
		{"reference_doctype": "Subcontracting Receipt", "reference_name": subcontracting_receipt, "docstatus": ["!=", 2]},
		"name"
	)
	if existing_gp:
		if not scr_doc.custom_gate_pass:
			scr_doc.db_set("custom_gate_pass", existing_gp)
		return {"gate_pass": existing_gp}

	# Create new Gate Pass
	gp_doc = frappe.new_doc("Gate Pass")
	gp_doc.gate_pass_type = "Inward"
	gp_doc.transaction_date = scr_doc.posting_date
	gp_doc.company = scr_doc.company
	gp_doc.reference_doctype = "Subcontracting Receipt"
	gp_doc.reference_name = subcontracting_receipt
	
	subcontractor = scr_doc.get("supplier") or scr_doc.get("subcontractor")
	if not subcontractor:
		frappe.throw(
			_("Could not identify the Subcontractor / Supplier for this Subcontracting Receipt."),
			title="Subcontractor Missing"
		)
	gp_doc.subcontractor = subcontractor

	# Add items
	for item in scr_doc.items:
		gp_doc.append("items", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"qty": item.qty,
			"uom": item.get("stock_uom") or item.get("uom"),
			"rate": item.get("rate") or 0,
			"amount": item.get("amount") or 0
		})

	gp_doc.insert(ignore_permissions=True)
	
	# Update link in Subcontracting Receipt
	scr_doc.db_set("custom_gate_pass", gp_doc.name)

	return {"gate_pass": gp_doc.name}


@frappe.whitelist()
def create_purchase_receipt_inward_flow(purchase_receipt):
	"""
	Automatically creates an Inward 'Gate Pass' document from a subcontracted 'Purchase Receipt' (Draft).
	"""
	if not purchase_receipt:
		frappe.throw(_("Purchase Receipt name is required."))

	pr_doc = frappe.get_doc("Purchase Receipt", purchase_receipt)

	# Check if Gate Pass already exists
	existing_gp = frappe.db.get_value(
		"Gate Pass",
		{"reference_doctype": "Purchase Receipt", "reference_name": purchase_receipt, "docstatus": ["!=", 2]},
		"name"
	)
	if existing_gp:
		if not pr_doc.custom_gate_pass:
			pr_doc.db_set("custom_gate_pass", existing_gp)
		return {"gate_pass": existing_gp}

	# Create new Gate Pass
	gp_doc = frappe.new_doc("Gate Pass")
	gp_doc.gate_pass_type = "Inward"
	gp_doc.transaction_date = pr_doc.posting_date
	gp_doc.company = pr_doc.company
	gp_doc.reference_doctype = "Purchase Receipt"
	gp_doc.reference_name = purchase_receipt
	
	subcontractor = pr_doc.get("supplier") or pr_doc.get("subcontractor")
	if not subcontractor:
		frappe.throw(
			_("Could not identify the Subcontractor / Supplier for this Purchase Receipt."),
			title="Subcontractor Missing"
		)
	gp_doc.subcontractor = subcontractor

	# Add items
	for item in pr_doc.items:
		gp_doc.append("items", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"qty": item.qty,
			"uom": item.get("stock_uom") or item.get("uom"),
			"rate": item.get("rate") or 0,
			"amount": item.get("amount") or 0
		})

	gp_doc.insert(ignore_permissions=True)
	
	# Update link in Purchase Receipt
	pr_doc.db_set("custom_gate_pass", gp_doc.name)

	return {"gate_pass": gp_doc.name}


@frappe.whitelist()
def create_subcontract_outward_flow(purchase_order):
	"""
	Automatically creates an Outward 'Gate Pass' document from a subcontracted 'Purchase Order' (Submitted).
	"""
	if not purchase_order:
		frappe.throw(_("Purchase Order name is required."))

	po_doc = frappe.get_doc("Purchase Order", purchase_order)

	# Check if Gate Pass already exists
	existing_gp = frappe.db.get_value(
		"Gate Pass",
		{"reference_doctype": "Purchase Order", "reference_name": purchase_order, "docstatus": ["!=", 2]},
		"name"
	)
	if existing_gp:
		if not po_doc.custom_gate_pass:
			po_doc.db_set("custom_gate_pass", existing_gp)
		return {"gate_pass": existing_gp}

	# Create new Gate Pass
	gp_doc = frappe.new_doc("Gate Pass")
	gp_doc.gate_pass_type = "Outward"
	gp_doc.transaction_date = po_doc.transaction_date
	gp_doc.company = po_doc.company
	gp_doc.reference_doctype = "Purchase Order"
	gp_doc.reference_name = purchase_order
	
	subcontractor = po_doc.get("supplier") or po_doc.get("subcontractor")
	if not subcontractor:
		frappe.throw(
			_("Could not identify the Subcontractor / Supplier for this Purchase Order."),
			title="Subcontractor Missing"
		)
	gp_doc.subcontractor = subcontractor

	# Add items
	for item in po_doc.items:
		gp_doc.append("items", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"qty": item.qty,
			"uom": item.get("stock_uom") or item.get("uom"),
			"rate": item.get("rate") or 0,
			"amount": item.get("amount") or 0
		})

	gp_doc.insert(ignore_permissions=True)
	
	# Update link in Purchase Order
	po_doc.db_set("custom_gate_pass", gp_doc.name)

	return {"gate_pass": gp_doc.name}

