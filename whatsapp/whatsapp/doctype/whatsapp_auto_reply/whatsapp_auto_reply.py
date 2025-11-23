# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import re


class WhatsAppAutoReply(Document):
	pass


def check_auto_reply(connection, from_number, message_content):
	"""Check if message matches any auto-reply rules"""
	try:
		# Get active auto-reply rules for this connection
		rules = frappe.get_all(
			"WhatsApp Auto Reply",
			filters={
				"active": 1,
				"connection": ["in", [connection, ""]]
			},
			fields=["name", "trigger_type", "trigger_value", "reply_template", "custom_reply", "priority"],
			order_by="priority asc"
		)
		
		for rule in rules:
			matched = False
			
			if rule.trigger_type == "All Messages":
				matched = True
			elif rule.trigger_type == "Keyword":
				if rule.trigger_value.lower() in message_content.lower():
					matched = True
			elif rule.trigger_type == "Pattern":
				if re.search(rule.trigger_value, message_content, re.IGNORECASE):
					matched = True
			elif rule.trigger_type == "First Message":
				# Check if this is first message from contact
				message_count = frappe.db.count("WhatsApp Message Log", {
					"contact": from_number,
					"direction": "Inbound"
				})
				if message_count == 1:
					matched = True
			
			if matched:
				send_auto_reply(connection, from_number, rule)
				return True
		
		return False
		
	except Exception as e:
		frappe.log_error(f"Auto Reply Check Error: {str(e)}")
		return False


def send_auto_reply(connection, recipient, rule):
	"""Send auto-reply message"""
	try:
		from whatsapp.whatsapp.api.whatsapp_api import send_message
		
		if rule.reply_template:
			template = frappe.get_doc("WhatsApp Message Template", rule.reply_template)
			message_obj = template.get_message_object()
			
			send_message(
				connection=connection,
				recipient=recipient,
				message_type=template.template_type,
				content=template.content,
				media_url=template.media_url or template.media_file,
				template=rule.reply_template
			)
		elif rule.custom_reply:
			send_message(
				connection=connection,
				recipient=recipient,
				message_type="Text",
				content=rule.custom_reply
			)
		
		frappe.log_error(f"Auto-reply sent to {recipient} using rule {rule.name}", "Auto Reply")
		
	except Exception as e:
		frappe.log_error(f"Send Auto Reply Error: {str(e)}")
