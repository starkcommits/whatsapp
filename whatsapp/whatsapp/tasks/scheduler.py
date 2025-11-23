# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe


def reset_daily_message_counters():
	"""Reset daily message counters for all connections"""
	try:
		connections = frappe.get_all("WhatsApp Connection", fields=["name"])
		for conn in connections:
			doc = frappe.get_doc("WhatsApp Connection", conn.name)
			doc.reset_daily_counter()
		
		frappe.db.commit()
		frappe.logger().info("Daily message counters reset successfully")
		
	except Exception as e:
		frappe.log_error(f"Error resetting daily counters: {str(e)}")


def reset_monthly_message_counters():
	"""Reset monthly message counters for all connections"""
	try:
		connections = frappe.get_all("WhatsApp Connection", fields=["name"])
		for conn in connections:
			doc = frappe.get_doc("WhatsApp Connection", conn.name)
			doc.reset_monthly_counter()
		
		frappe.db.commit()
		frappe.logger().info("Monthly message counters reset successfully")
		
	except Exception as e:
		frappe.log_error(f"Error resetting monthly counters: {str(e)}")


def update_campaign_statistics():
	"""Update statistics for running campaigns"""
	try:
		campaigns = frappe.get_all(
			"WhatsApp Campaign",
			filters={"status": "Running"},
			fields=["name"]
		)
		
		for campaign in campaigns:
			doc = frappe.get_doc("WhatsApp Campaign", campaign.name)
			doc.update_statistics()
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error updating campaign statistics: {str(e)}")


def update_contact_segments():
	"""Update contact counts for auto-updating segments"""
	try:
		segments = frappe.get_all(
			"WhatsApp Contact Segment",
			filters={"auto_update": 1},
			fields=["name"]
		)
		
		for segment in segments:
			doc = frappe.get_doc("WhatsApp Contact Segment", segment.name)
			doc.update_contact_count()
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error updating contact segments: {str(e)}")
