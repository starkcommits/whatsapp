# Copyright (c) 2025, INIA GLOBAL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import re


class WhatsAppMessageTemplate(Document):
	def validate(self):
		"""Validate template and extract variables"""
		if self.content:
			# Extract variables from content
			variables = re.findall(r'\{\{(\w+)\}\}', self.content)
			if variables:
				self.variables = json.dumps(list(set(variables)))

	def render(self, context=None):
		"""Render template with context variables"""
		if not context:
			context = {}
		
		content = self.content
		
		# Replace variables
		for key, value in context.items():
			content = content.replace(f"{{{{{key}}}}}", str(value))
		
		return content

	def get_message_object(self, context=None):
		"""Get WhatsApp message object for sending"""
		message = {}
		
		if self.template_type == "Text":
			message = {
				"text": self.render(context)
			}
		elif self.template_type == "Image":
			message = {
				"image": {
					"url": self.media_url or self.media_file
				},
				"caption": self.render(context)
			}
		elif self.template_type == "Video":
			message = {
				"video": {
					"url": self.media_url or self.media_file
				},
				"caption": self.render(context)
			}
		elif self.template_type == "Audio":
			message = {
				"audio": {
					"url": self.media_url or self.media_file
				}
			}
		elif self.template_type == "Document":
			message = {
				"document": {
					"url": self.media_url or self.media_file
				},
				"caption": self.render(context)
			}
		
		return message


@frappe.whitelist()
def preview_template(template_name, context=None):
	"""Preview template with sample context"""
	doc = frappe.get_doc("WhatsApp Message Template", template_name)
	
	if context and isinstance(context, str):
		context = json.loads(context)
	
	return {
		"rendered_content": doc.render(context),
		"message_object": doc.get_message_object(context)
	}
