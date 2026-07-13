# Copyright (c) 2026, Meet Panara and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 120,
		},
		{
			"label": _("Transaction Date"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Delivered Qty"),
			"fieldname": "delivered_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Billed Amount"),
			"fieldname": "billed_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 120,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]


def get_data(filters: dict) -> list[dict]:
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("so.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")
		values["customer"] = filters["customer"]

	if filters.get("from_date"):
		conditions.append("so.transaction_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("so.transaction_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	# Only show submitted sales orders (docstatus = 1)
	conditions.append("so.docstatus = 1")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	query = f"""
		SELECT
			so.customer,
			so.customer_name,
			so.name as sales_order,
			so.transaction_date,
			so.status,
			so_item.item_code,
			so_item.item_name,
			so_item.qty,
			so_item.base_rate as rate,
			so_item.base_amount as amount,
			so_item.delivered_qty,
			(so_item.billed_amt * so.conversion_rate) as billed_amount,
			so.territory,
			so.project,
			so.company,
			so.company as currency
		FROM
			`tabSales Order` so
		INNER JOIN
			`tabSales Order Item` so_item ON so_item.parent = so.name
		WHERE
			{where_clause}
		ORDER BY
			so.transaction_date DESC, so.customer ASC
	"""

	data = frappe.db.sql(query, values, as_dict=True)

	for row in data:
		row["currency"] = frappe.get_cached_value("Company", row["company"], "default_currency")

	return data
