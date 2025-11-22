# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class WhatsAppContact(Document):
	def validate(self):
		"""Validate phone number and custom fields"""
		if self.phone_number:
			# Clean phone number
			phone = self.phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
			if not phone.replace("+", "").isdigit():
				frappe.throw("Phone number must contain only digits")
			self.phone_number = phone
			
			# Set WhatsApp ID format
			if not self.whatsapp_id:
				self.whatsapp_id = f"{phone.replace('+', '')}@s.whatsapp.net"
		
		# Validate custom fields JSON
		if self.custom_fields:
			try:
				json.loads(self.custom_fields)
			except json.JSONDecodeError:
				frappe.throw("Custom fields must be valid JSON")

	def opt_in(self):
		"""Mark contact as opted in"""
		self.opt_in_status = "Opted In"
		self.opt_in_date = frappe.utils.now()
		self.opt_out_date = None
		self.save()

	def opt_out(self):
		"""Mark contact as opted out"""
		self.opt_in_status = "Opted Out"
		self.opt_out_date = frappe.utils.now()
		self.save()

	def add_tag(self, tag_name):
		"""Add a tag to the contact"""
		existing_tags = [row.tag for row in self.tags]
		if tag_name not in existing_tags:
			self.append("tags", {"tag": tag_name})
			self.save()

	def remove_tag(self, tag_name):
		"""Remove a tag from the contact"""
		for row in self.tags:
			if row.tag == tag_name:
				self.remove(row)
				break
		self.save()

	def update_message_stats(self, message_type, direction):
		"""Update message statistics"""
		self.last_message_date = frappe.utils.now()
		self.last_message_type = message_type
		
		if direction == "Outbound":
			self.total_messages_sent += 1
		elif direction == "Inbound":
			self.total_messages_received += 1
		
		self.save(ignore_permissions=True)


@frappe.whitelist()
def import_contacts(contacts_data):
	"""Bulk import contacts from JSON data"""
	try:
		contacts = json.loads(contacts_data) if isinstance(contacts_data, str) else contacts_data
		imported = 0
		errors = []
		
		for contact in contacts:
			try:
				phone = contact.get("phone_number")
				if not phone:
					errors.append(f"Missing phone number in contact: {contact}")
					continue
				
				# Check if contact exists
				if frappe.db.exists("WhatsApp Contact", phone):
					# Update existing contact
					doc = frappe.get_doc("WhatsApp Contact", phone)
				else:
					# Create new contact
					doc = frappe.new_doc("WhatsApp Contact")
					doc.phone_number = phone
				
				# Update fields
				if contact.get("name"):
					doc.name1 = contact.get("name")
				if contact.get("email"):
					doc.email = contact.get("email")
				if contact.get("opt_in_status"):
					doc.opt_in_status = contact.get("opt_in_status")
				if contact.get("tags"):
					for tag in contact.get("tags"):
						doc.add_tag(tag)
				
				doc.save(ignore_permissions=True)
				imported += 1
				
			except Exception as e:
				errors.append(f"Error importing {contact.get('phone_number', 'unknown')}: {str(e)}")
		
		return {
			"success": True,
			"imported": imported,
			"errors": errors
		}
		
	except Exception as e:
		frappe.log_error(f"Contact Import Error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_contact_by_phone(phone_number):
	"""Get contact by phone number"""
	if frappe.db.exists("WhatsApp Contact", phone_number):
		return frappe.get_doc("WhatsApp Contact", phone_number).as_dict()
	return None
