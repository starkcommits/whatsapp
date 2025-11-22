# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import requests


class WhatsAppConnection(Document):
	def validate(self):
		"""Validate phone number format"""
		if self.phone_number:
			# Remove any non-numeric characters except +
			phone = self.phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
			if not phone.replace("+", "").isdigit():
				frappe.throw("Phone number must contain only digits")
			self.phone_number = phone

	def on_update(self):
		"""Handle connection updates"""
		if self.has_value_changed("status"):
			if self.status == "Connected":
				self.last_connected = frappe.utils.now()
			elif self.status == "Disconnected":
				self.last_disconnected = frappe.utils.now()

	def connect(self):
		"""Initiate WhatsApp connection"""
		try:
			# Call Node.js service to initiate connection
			response = requests.post(
				f"{self.get_node_service_url()}/api/connect",
				json={
					"connection_id": self.name,
					"phone_number": self.phone_number,
					"connection_method": self.connection_method,
					"browser_name": self.browser_name,
					"browser_version": self.browser_version,
					"mark_online_on_connect": self.mark_online_on_connect,
					"sync_full_history": self.sync_full_history
				},
				timeout=10
			)
			
			if response.status_code == 200:
				data = response.json()
				self.status = "Connecting"
				
				if self.connection_method == "Pairing Code" and data.get("pairing_code"):
					self.pairing_code = data.get("pairing_code")
				
				self.save()
				frappe.msgprint(f"Connection initiated. Status: {self.status}")
				return data
			else:
				frappe.throw(f"Failed to connect: {response.text}")
				
		except Exception as e:
			frappe.log_error(f"WhatsApp Connection Error: {str(e)}")
			self.status = "Failed"
			self.save()
			frappe.throw(f"Connection failed: {str(e)}")

	def disconnect(self):
		"""Disconnect WhatsApp connection"""
		try:
			response = requests.post(
				f"{self.get_node_service_url()}/api/disconnect",
				json={"connection_id": self.name},
				timeout=10
			)
			
			if response.status_code == 200:
				self.status = "Disconnected"
				self.last_disconnected = frappe.utils.now()
				self.save()
				frappe.msgprint("Disconnected successfully")
			else:
				frappe.throw(f"Failed to disconnect: {response.text}")
				
		except Exception as e:
			frappe.log_error(f"WhatsApp Disconnect Error: {str(e)}")
			frappe.throw(f"Disconnect failed: {str(e)}")

	def get_node_service_url(self):
		"""Get Node.js service URL from site config"""
		return frappe.conf.get("whatsapp_node_service_url", "http://localhost:3000")

	def check_rate_limit(self):
		"""Check if rate limit is exceeded"""
		if self.messages_sent_today >= self.daily_message_limit:
			return False, "Daily message limit exceeded"
		
		if self.messages_sent_this_month >= self.monthly_message_limit:
			return False, "Monthly message limit exceeded"
		
		return True, "OK"

	def increment_message_count(self):
		"""Increment message counters"""
		self.db_set("messages_sent_today", self.messages_sent_today + 1)
		self.db_set("messages_sent_this_month", self.messages_sent_this_month + 1)

	def reset_daily_counter(self):
		"""Reset daily message counter (called by scheduler)"""
		self.db_set("messages_sent_today", 0)

	def reset_monthly_counter(self):
		"""Reset monthly message counter (called by scheduler)"""
		self.db_set("messages_sent_this_month", 0)


@frappe.whitelist()
def connect_whatsapp(connection_name):
	"""API method to connect WhatsApp"""
	doc = frappe.get_doc("WhatsApp Connection", connection_name)
	return doc.connect()


@frappe.whitelist()
def disconnect_whatsapp(connection_name):
	"""API method to disconnect WhatsApp"""
	doc = frappe.get_doc("WhatsApp Connection", connection_name)
	return doc.disconnect()


@frappe.whitelist()
def get_connection_status(connection_name):
	"""Get current connection status"""
	doc = frappe.get_doc("WhatsApp Connection", connection_name)
	return {
		"status": doc.status,
		"last_connected": doc.last_connected,
		"messages_sent_today": doc.messages_sent_today,
		"messages_sent_this_month": doc.messages_sent_this_month,
		"daily_limit": doc.daily_message_limit,
		"monthly_limit": doc.monthly_message_limit
	}
