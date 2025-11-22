# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
import json


@frappe.whitelist(allow_guest=True)
def handle_event(connection_id, event, data):
	"""Handle events from Node.js service"""
	try:
		data = json.loads(data) if isinstance(data, str) else data
		
		if event == 'qr_code':
			# Update connection with QR code
			doc = frappe.get_doc("WhatsApp Connection", connection_id)
			doc.qr_code = f'<div id="qr-code-{connection_id}"><pre>{data.get("qr", "")}</pre></div>'
			doc.save(ignore_permissions=True)
			
		elif event == 'pairing_code':
			# Update connection with pairing code
			doc = frappe.get_doc("WhatsApp Connection", connection_id)
			doc.pairing_code = data.get("code")
			doc.save(ignore_permissions=True)
		
		return {"success": True}
		
	except Exception as e:
		frappe.log_error(f"Webhook Event Error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def update_connection_status(connection_id, status):
	"""Update connection status from Node.js service"""
	try:
		doc = frappe.get_doc("WhatsApp Connection", connection_id)
		doc.status = status
		
		if status == "Connected":
			doc.last_connected = frappe.utils.now()
		elif status == "Disconnected":
			doc.last_disconnected = frappe.utils.now()
		
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		
		return {"success": True}
		
	except Exception as e:
		frappe.log_error(f"Connection Status Update Error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def save_incoming_message(connection_id, from_number, message_id, message_type, content, timestamp):
	"""Save incoming message from Node.js service"""
	try:
		# Clean phone number
		phone = from_number.replace("@s.whatsapp.net", "").replace("@g.us", "")
		
		# Check if contact exists, create if not
		if not frappe.db.exists("WhatsApp Contact", phone):
			contact = frappe.get_doc({
				"doctype": "WhatsApp Contact",
				"phone_number": phone,
				"whatsapp_id": from_number,
				"opt_in_status": "Opted In"
			})
			contact.insert(ignore_permissions=True)
		
		# Create message log
		message_log = frappe.get_doc({
			"doctype": "WhatsApp Message Log",
			"message_id": message_id,
			"direction": "Inbound",
			"contact": phone,
			"message_type": message_type,
			"content": content,
			"status": "Received",
			"timestamp": frappe.utils.get_datetime(timestamp)
		})
		message_log.insert(ignore_permissions=True)
		frappe.db.commit()
		
		return {"success": True, "message_log_id": message_log.name}
		
	except Exception as e:
		frappe.log_error(f"Save Incoming Message Error: {str(e)}")
		return {"success": False, "error": str(e)}
