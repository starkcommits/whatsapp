# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppMessageLog(Document):
	def on_update(self):
		"""Update contact statistics when message status changes"""
		if self.has_value_changed("status") and self.contact:
			try:
				contact = frappe.get_doc("WhatsApp Contact", self.contact)
				contact.update_message_stats(self.message_type, self.direction)
			except Exception as e:
				frappe.log_error(f"Error updating contact stats: {str(e)}")

	def mark_sent(self, message_id=None):
		"""Mark message as sent"""
		self.status = "Sent"
		self.sent_at = frappe.utils.now()
		if message_id:
			self.message_id = message_id
		self.save(ignore_permissions=True)

	def mark_delivered(self):
		"""Mark message as delivered"""
		self.status = "Delivered"
		self.delivered_at = frappe.utils.now()
		self.save(ignore_permissions=True)

	def mark_read(self):
		"""Mark message as read"""
		self.status = "Read"
		self.read_at = frappe.utils.now()
		self.save(ignore_permissions=True)

	def mark_failed(self, error_message):
		"""Mark message as failed"""
		self.status = "Failed"
		self.failed_at = frappe.utils.now()
		self.error_message = error_message
		self.save(ignore_permissions=True)


@frappe.whitelist()
def update_message_status(message_log_id, status, **kwargs):
	"""Update message status from Node.js service"""
	try:
		doc = frappe.get_doc("WhatsApp Message Log", message_log_id)
		
		if status == "Sent":
			doc.mark_sent(kwargs.get("message_id"))
		elif status == "Delivered":
			doc.mark_delivered()
		elif status == "Read":
			doc.mark_read()
		elif status == "Failed":
			doc.mark_failed(kwargs.get("error_message", "Unknown error"))
		
		# Update campaign statistics if this is part of a campaign
		if doc.campaign:
			campaign = frappe.get_doc("WhatsApp Campaign", doc.campaign)
			campaign.update_statistics()
		
		return {"success": True}
		
	except Exception as e:
		frappe.log_error(f"Error updating message status: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_conversation(contact):
	"""Get conversation history with a contact"""
	messages = frappe.get_all(
		"WhatsApp Message Log",
		filters={"contact": contact},
		fields=["name", "direction", "message_type", "content", "timestamp", "status"],
		order_by="timestamp desc",
		limit=100
	)
	return messages
