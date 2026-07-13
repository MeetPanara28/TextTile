# Copyright (c) 2026, Meet Panara and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today
from frappe import _


class WhatsAppOrderRequest(Document):
	pass


@frappe.whitelist()
def create_sales_order_from_request(request_name):
	try:
		return _create_sales_order_from_request_impl(request_name)
	except Exception as e:
		import traceback
		tb = traceback.format_exc()
		try:
			with open("/home/user/Royal_ERP/frappe_royal/debug_error.log", "a") as f:
				f.write(f"\n--- ERROR FOR {request_name} ---\n{tb}\n")
		except Exception:
			pass
		frappe.log_error(title="WhatsApp SO Creation Error", message=tb)
		raise e


def _create_sales_order_from_request_impl(request_name):
	# Load the WhatsApp Order Request doc
	req_doc = frappe.get_doc("WhatsApp Order Request", request_name)
	
	if req_doc.status != "Pending":
		frappe.throw(_("Sales Order can only be created for Pending requests."))
		
	if not req_doc.customer:
		frappe.throw(_("Please link a Customer to this request first."))
		
	if not req_doc.parsed_item:
		frappe.throw(_("Please select an Item first to create a Sales Order."))
		
	item_code = req_doc.parsed_item
		
	# Determine default company
	company = frappe.db.get_default("Company")
	if not company:
		companies = frappe.db.get_all("Company", fields=["name"])
		if companies:
			company = companies[0].name
		else:
			frappe.throw(_("Please configure a Company in ERPNext first."))
			
	# Fetch defaults (UOM, Warehouse, Rate) using erpnext.stock.get_item_details
	uom = None
	warehouse = None
	rate = 0.0
	price_list_rate = 0.0
	
	try:
		from erpnext.stock.get_item_details import get_item_details
		currency = frappe.db.get_value("Customer", req_doc.customer, "default_currency") or \
			frappe.db.get_value("Company", company, "default_currency") or "INR"
		price_list = frappe.db.get_value("Customer", req_doc.customer, "default_price_list") or "Standard Selling"
		
		args = frappe._dict({
			"item_code": item_code,
			"company": company,
			"customer": req_doc.customer,
			"doctype": "Sales Order",
			"qty": req_doc.parsed_qty or 1.0,
			"price_list": price_list,
			"currency": currency,
			"transaction_date": today(),
		})
		details = get_item_details(args)
		if details:
			uom = details.get("uom")
			warehouse = details.get("warehouse")
			rate = details.get("rate") or details.get("price_list_rate") or 0.0
			price_list_rate = details.get("price_list_rate") or 0.0
	except Exception:
		pass
		
	if not uom:
		uom = frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"
	if not warehouse:
		warehouse = frappe.db.get_value("Item", item_code, "default_warehouse") or \
			frappe.db.get_value("Company", company, "default_warehouse")
			
	# Create Sales Order
	so = frappe.get_doc({
		"doctype": "Sales Order",
		"customer": req_doc.customer,
		"company": company,
		"delivery_date": add_days(today(), 7),
		"items": [{
			"item_code": item_code,
			"qty": req_doc.parsed_qty or 1.0,
			"uom": uom,
			"warehouse": warehouse,
			"rate": rate,
			"price_list_rate": price_list_rate,
			"delivery_date": add_days(today(), 7)
		}]
	})
	
	if hasattr(so, "set_missing_values"):
		so.set_missing_values()
		
	try:
		so.insert(ignore_permissions=True)
		so.save(ignore_permissions=True)
	except frappe.ValidationError as e:
		frappe.throw(_("Could not create Sales Order: {0}").format(str(e)))
	except Exception as e:
		frappe.throw(_("Failed to save Sales Order draft: {0}").format(str(e)))
	
	# Update request status
	req_doc.status = "Sales Order Created"
	req_doc.sales_order = so.name
	req_doc.save(ignore_permissions=True)
	
	frappe.db.commit()
	return so.name

