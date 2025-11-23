# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class WhatsAppContactSegment(Document):
	def validate(self):
		"""Validate filter conditions JSON"""
		if self.filter_conditions:
			try:
				json.loads(self.filter_conditions)
			except json.JSONDecodeError:
				frappe.throw("Filter conditions must be valid JSON")

	def on_update(self):
		"""Update contact count when segment is updated"""
		if self.auto_update:
			self.update_contact_count()

	def update_contact_count(self):
		"""Update the contact count based on filter conditions"""
		try:
			contacts = self.get_contacts()
			self.db_set("contact_count", len(contacts))
			self.db_set("last_updated", frappe.utils.now())
		except Exception as e:
			frappe.log_error(f"Error updating contact count: {str(e)}")

	def get_contacts(self):
		"""Get contacts matching the segment filters"""
		try:
			if not self.filter_conditions:
				return []
			
			filters = json.loads(self.filter_conditions)
			
			# Build query based on filters
			query = frappe.db.get_all(
				"WhatsApp Contact",
				filters=self._build_filters(filters),
				fields=["name", "phone_number", "name1", "opt_in_status"]
			)
			
			return query
			
		except Exception as e:
			frappe.log_error(f"Error getting segment contacts: {str(e)}")
			return []

	def _build_filters(self, filter_conditions):
		"""Build Frappe filters from JSON conditions"""
		filters = {}
		
		# Example filter structure:
		# {
		#   "opt_in_status": "Opted In",
		#   "tags": ["VIP", "Active"],
		#   "custom_field": {"city": "New York"}
		# }
		
		for key, value in filter_conditions.items():
			if key == "tags":
				# Handle tag filtering separately
				continue
			elif key == "custom_field":
				# Handle custom field filtering
				continue
			else:
				filters[key] = value
		
		return filters


@frappe.whitelist()
def get_segment_contacts(segment_name):
	"""API method to get contacts in a segment"""
	doc = frappe.get_doc("WhatsApp Contact Segment", segment_name)
	return doc.get_contacts()


@frappe.whitelist()
def refresh_segment(segment_name):
	"""Refresh segment contact count"""
	doc = frappe.get_doc("WhatsApp Contact Segment", segment_name)
	doc.update_contact_count()
	return {
		"contact_count": doc.contact_count,
		"last_updated": doc.last_updated
	}
