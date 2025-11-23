# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
import json
import requests


@frappe.whitelist()
def send_message(connection, recipient, message_type, content, media_url=None, template=None):
	"""Send a WhatsApp message"""
	try:
		# Get connection
		conn = frappe.get_doc("WhatsApp Connection", connection)
		
		# Check rate limit
		can_send, message = conn.check_rate_limit()
		if not can_send:
			return {"success": False, "error": message}
		
		# Prepare message object
		message_obj = {}
		
		if message_type == "Text":
			message_obj = {"text": content}
		elif message_type == "Image":
			message_obj = {
				"image": {"url": media_url},
				"caption": content
			}
		elif message_type == "Video":
			message_obj = {
				"video": {"url": media_url},
				"caption": content
			}
		elif message_type == "Audio":
			message_obj = {
				"audio": {"url": media_url}
			}
		elif message_type == "Document":
			message_obj = {
				"document": {"url": media_url},
				"caption": content
			}
		
		# Create message log
		message_log = frappe.get_doc({
			"doctype": "WhatsApp Message Log",
			"direction": "Outbound",
			"contact": recipient,
			"message_type": message_type,
			"content": content,
			"media_url": media_url,
			"template": template,
			"status": "Queued"
		})
		message_log.insert()
		
		# Send to Node.js service
		node_service_url = conn.get_node_service_url()
		response = requests.post(
			f"{node_service_url}/api/queue-message",
			json={
				"connection_id": connection,
				"message_log_id": message_log.name,
				"recipient": recipient,
				"message": message_obj
			},
			timeout=5
		)
		
		if response.status_code == 200:
			conn.increment_message_count()
			return {"success": True, "message_log_id": message_log.name}
		else:
			message_log.mark_failed(f"Failed to queue: {response.text}")
			return {"success": False, "error": response.text}
		
	except Exception as e:
		frappe.log_error(f"Send Message Error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_contact_info(connection, phone_number):
	"""Get contact information from WhatsApp"""
	try:
		conn = frappe.get_doc("WhatsApp Connection", connection)
		node_service_url = conn.get_node_service_url()
		
		response = requests.post(
			f"{node_service_url}/api/get-contact-info",
			json={
				"connection_id": connection,
				"phone_number": phone_number
			},
			timeout=5
		)
		
		if response.status_code == 200:
			return response.json()
		else:
			return {"success": False, "error": response.text}
		
	except Exception as e:
		frappe.log_error(f"Get Contact Info Error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def upload_media(file_url):
	"""Upload media file for WhatsApp"""
	try:
		# This would handle media upload to WhatsApp servers
		# For now, return the file URL
		return {"success": True, "media_url": file_url}
		
	except Exception as e:
		frappe.log_error(f"Upload Media Error: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_service_status():
	"""Get Node.js service status"""
	try:
		# Get any active connection to get service URL
		connections = frappe.get_all("WhatsApp Connection", limit=1)
		if not connections:
			return {"success": False, "error": "No connections configured"}
		
		conn = frappe.get_doc("WhatsApp Connection", connections[0].name)
		node_service_url = conn.get_node_service_url()
		
		response = requests.get(f"{node_service_url}/api/status", timeout=5)
		
		if response.status_code == 200:
			return response.json()
		else:
			return {"success": False, "error": "Service not responding"}
		
	except Exception as e:
		return {"success": False, "error": str(e)}
