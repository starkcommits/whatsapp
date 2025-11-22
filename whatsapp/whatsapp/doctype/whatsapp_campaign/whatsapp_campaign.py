# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import json


class WhatsAppCampaign(Document):
	def validate(self):
		"""Validate campaign settings"""
		if self.schedule_type == "Scheduled" and not self.schedule_datetime:
			frappe.throw("Schedule Date & Time is required for scheduled campaigns")
		
		# Get total contacts from segment
		if self.target_segment:
			segment = frappe.get_doc("WhatsApp Contact Segment", self.target_segment)
			self.total_contacts = segment.contact_count

	def before_submit(self):
		"""Validate before starting campaign"""
		# Check connection status
		connection = frappe.get_doc("WhatsApp Connection", self.connection)
		if connection.status != "Connected":
			frappe.throw("WhatsApp connection is not active")
		
		# Check rate limits
		can_send, message = connection.check_rate_limit()
		if not can_send:
			frappe.throw(message)

	def start_campaign(self):
		"""Start the campaign"""
		try:
			self.status = "Running"
			self.started_at = frappe.utils.now()
			self.save()
			
			# Get contacts from segment
			segment = frappe.get_doc("WhatsApp Contact Segment", self.target_segment)
			contacts = segment.get_contacts()
			
			# Get message template
			template = frappe.get_doc("WhatsApp Message Template", self.message_template)
			
			# Queue messages for sending
			for contact in contacts:
				self.queue_message(contact, template)
			
			frappe.msgprint(f"Campaign started. {len(contacts)} messages queued.")
			
		except Exception as e:
			self.status = "Failed"
			self.save()
			frappe.log_error(f"Campaign Start Error: {str(e)}")
			frappe.throw(f"Failed to start campaign: {str(e)}")

	def pause_campaign(self):
		"""Pause the campaign"""
		self.status = "Paused"
		self.save()
		frappe.msgprint("Campaign paused")

	def resume_campaign(self):
		"""Resume the campaign"""
		self.status = "Running"
		self.save()
		frappe.msgprint("Campaign resumed")

	def stop_campaign(self):
		"""Stop the campaign"""
		self.status = "Completed"
		self.completed_at = frappe.utils.now()
		self.save()
		frappe.msgprint("Campaign stopped")

	def queue_message(self, contact, template):
		"""Queue a message for sending"""
		try:
			# Create message log
			message_log = frappe.get_doc({
				"doctype": "WhatsApp Message Log",
				"campaign": self.name,
				"contact": contact.get("phone_number"),
				"direction": "Outbound",
				"message_type": template.template_type,
				"status": "Queued",
				"template": template.name
			})
			message_log.insert(ignore_permissions=True)
			
			# Send to Node.js service for processing
			self.send_to_queue(message_log.name, contact, template)
			
		except Exception as e:
			frappe.log_error(f"Error queuing message: {str(e)}")

	def send_to_queue(self, message_log_id, contact, template):
		"""Send message to Node.js queue"""
		try:
			connection = frappe.get_doc("WhatsApp Connection", self.connection)
			node_service_url = connection.get_node_service_url()
			
			# Prepare message context
			context = {
				"name": contact.get("name1", ""),
				"phone": contact.get("phone_number", "")
			}
			
			message_object = template.get_message_object(context)
			
			# Send to Node.js service
			response = requests.post(
				f"{node_service_url}/api/queue-message",
				json={
					"connection_id": self.connection,
					"message_log_id": message_log_id,
					"recipient": contact.get("phone_number"),
					"message": message_object,
					"campaign_id": self.name
				},
				timeout=5
			)
			
			if response.status_code != 200:
				frappe.log_error(f"Failed to queue message: {response.text}")
				
		except Exception as e:
			frappe.log_error(f"Error sending to queue: {str(e)}")

	def update_statistics(self):
		"""Update campaign statistics"""
		# Get message logs for this campaign
		stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total,
				SUM(CASE WHEN status = 'Sent' THEN 1 ELSE 0 END) as sent,
				SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered,
				SUM(CASE WHEN status = 'Read' THEN 1 ELSE 0 END) as read,
				SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as failed
			FROM `tabWhatsApp Message Log`
			WHERE campaign = %s
		""", self.name, as_dict=True)[0]
		
		self.messages_sent = stats.sent or 0
		self.messages_delivered = stats.delivered or 0
		self.messages_read = stats.read or 0
		self.messages_failed = stats.failed or 0
		
		# Calculate rates
		if self.messages_sent > 0:
			self.delivery_rate = (self.messages_delivered / self.messages_sent) * 100
			self.read_rate = (self.messages_read / self.messages_sent) * 100
		
		self.save(ignore_permissions=True)


@frappe.whitelist()
def start_campaign(campaign_name):
	"""API method to start campaign"""
	doc = frappe.get_doc("WhatsApp Campaign", campaign_name)
	return doc.start_campaign()


@frappe.whitelist()
def pause_campaign(campaign_name):
	"""API method to pause campaign"""
	doc = frappe.get_doc("WhatsApp Campaign", campaign_name)
	return doc.pause_campaign()


@frappe.whitelist()
def resume_campaign(campaign_name):
	"""API method to resume campaign"""
	doc = frappe.get_doc("WhatsApp Campaign", campaign_name)
	return doc.resume_campaign()


@frappe.whitelist()
def stop_campaign(campaign_name):
	"""API method to stop campaign"""
	doc = frappe.get_doc("WhatsApp Campaign", campaign_name)
	return doc.stop_campaign()


@frappe.whitelist()
def get_campaign_stats(campaign_name):
	"""Get campaign statistics"""
	doc = frappe.get_doc("WhatsApp Campaign", campaign_name)
	doc.update_statistics()
	return {
		"total_contacts": doc.total_contacts,
		"messages_sent": doc.messages_sent,
		"messages_delivered": doc.messages_delivered,
		"messages_read": doc.messages_read,
		"messages_failed": doc.messages_failed,
		"delivery_rate": doc.delivery_rate,
		"read_rate": doc.read_rate,
		"status": doc.status
	}
