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






