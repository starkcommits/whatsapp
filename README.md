# WhatsApp Marketing Application

A comprehensive WhatsApp marketing solution built with Frappe and Baileys library, providing campaign management, contact segmentation, automation, and analytics.

## Features

### 📱 Connection Management
- **Dual Authentication**: Support for both QR code and pairing code methods
- **Multi-Device**: Connect multiple WhatsApp accounts
- **Auto-Reconnect**: Automatic reconnection on disconnect
- **Rate Limiting**: Configurable daily and monthly message limits per connection

### 👥 Contact Management
- **Bulk Import**: Import contacts via CSV or JSON
- **Opt-in/Opt-out**: GDPR-compliant consent management
- **Tagging System**: Organize contacts with custom tags
- **Custom Fields**: Store additional contact data as JSON
- **Statistics Tracking**: Monitor message engagement per contact

### 🎯 Segmentation
- **Dynamic Segments**: Auto-updating contact groups based on filters
- **JSON Filters**: Flexible filtering with custom conditions
- **Real-time Updates**: Segment counts update automatically

### 📧 Campaign Management
- **Campaign Types**: Broadcast, drip, and triggered campaigns
- **Scheduling**: Immediate, scheduled, or recurring campaigns
- **Rate Control**: Configurable sending rates to avoid bans
- **Real-time Analytics**: Track sent, delivered, read, and failed messages
- **Delivery & Read Rates**: Automatic calculation of engagement metrics

### 💬 Message Templates
- **Multi-Media Support**: Text, images, videos, audio, documents
- **Variable Substitution**: Dynamic content with {{variable}} syntax
- **Template Categories**: Organize by marketing, transactional, OTP, etc.
- **Preview**: Preview messages before sending

### 🤖 Automation
- **Auto-Reply**: Keyword and pattern-based automatic responses
- **Priority System**: Control which rules fire first
- **First Message Detection**: Special handling for new contacts
- **Template Integration**: Use templates in auto-replies

### 📊 Analytics & Reporting
- **Campaign Statistics**: Comprehensive metrics per campaign
- **Message Logs**: Complete history of all messages
- **Conversation View**: See full conversation history with contacts
- **Status Tracking**: Real-time message status updates

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│  Frappe App     │◄───────►│  Node.js Service │◄───────►│   WhatsApp      │
│  (Python)       │   API   │  (Baileys)       │  WebSocket│   Servers      │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │
        │                            │
        ▼                            ▼
┌─────────────────┐         ┌──────────────────┐
│                 │         │                  │
│  MariaDB        │         │  Redis Queue     │
│  (Data)         │         │  (Bull)          │
│                 │         │                  │
└─────────────────┘         └──────────────────┘
```

## Installation

### Prerequisites
- Frappe Framework (v14 or v15)
- Node.js (v18 or higher)
- Redis Server
- Python 3.10+

### Step 1: Install Frappe App

```bash
cd ~/frappe-bench
bench get-app https://github.com/your-repo/whatsapp.git
bench --site your-site.local install-app whatsapp
```

### Step 2: Install Node.js Dependencies

```bash
cd ~/frappe-bench/apps/whatsapp
npm install
```

### Step 3: Configure Environment

Create a `.env` file in the app root:

```bash
cp .env.example .env
```

Edit `.env`:

```env
FRAPPE_SITE_URL=http://localhost:8000
NODE_SERVICE_PORT=3000
REDIS_HOST=localhost
REDIS_PORT=6379
LOG_LEVEL=info
AUTH_FOLDER=./auth_info_baileys
```

### Step 4: Configure Frappe Site

Add to `site_config.json`:

```json
{
  "whatsapp_node_service_url": "http://localhost:3000"
}
```

### Step 5: Start Node.js Service

```bash
cd ~/frappe-bench/apps/whatsapp
npm start
```

Or use PM2 for production:

```bash
pm2 start node_service/index.js --name whatsapp-service
pm2 save
```

### Step 6: Start Redis (if not running)

```bash
redis-server
```

## Usage

### 1. Create a WhatsApp Connection

1. Go to **WhatsApp > WhatsApp Connection**
2. Click **New**
3. Fill in:
   - Connection Name
   - Phone Number (with country code, e.g., +1234567890)
   - Connection Method (QR Code or Pairing Code)
   - Daily/Monthly Message Limits
4. Save
5. Click **Connect** button
6. If QR Code: Scan with WhatsApp app
7. If Pairing Code: Enter code in WhatsApp app

### 2. Import Contacts

**Method 1: Manual Entry**
- Go to **WhatsApp > WhatsApp Contact**
- Create contacts one by one

**Method 2: Bulk Import**
```python
import frappe
from whatsapp.whatsapp.doctype.whatsapp_contact.whatsapp_contact import import_contacts

contacts = [
    {
        "phone_number": "+1234567890",
        "name": "John Doe",
        "email": "john@example.com",
        "opt_in_status": "Opted In",
        "tags": ["VIP", "Customer"]
    }
]

import_contacts(contacts)
```

### 3. Create a Segment

1. Go to **WhatsApp > WhatsApp Contact Segment**
2. Create a new segment
3. Add filter conditions (JSON):

```json
{
  "opt_in_status": "Opted In",
  "tags": ["VIP"]
}
```

### 4. Create a Message Template

1. Go to **WhatsApp > WhatsApp Message Template**
2. Create template with variables:

```
Hello {{name}}, 

Your order #{{order_id}} has been shipped!

Track here: {{tracking_url}}
```

### 5. Create and Run a Campaign

1. Go to **WhatsApp > WhatsApp Campaign**
2. Fill in:
   - Campaign Name
   - Select Connection
   - Select Target Segment
   - Select Message Template
   - Set Schedule Type
   - Configure Sending Rate
3. Save
4. Click **Start Campaign**

### 6. Set Up Auto-Replies

1. Go to **WhatsApp > WhatsApp Auto Reply**
2. Create rule:
   - Trigger Type: Keyword
   - Trigger Value: "hello"
   - Reply Template: Select template
3. Save and activate

## API Reference

### Send Message

```python
from whatsapp.whatsapp.api.whatsapp_api import send_message

result = send_message(
    connection="My Connection",
    recipient="+1234567890",
    message_type="Text",
    content="Hello from Frappe!"
)
```

### Get Conversation

```python
from whatsapp.whatsapp.doctype.whatsapp_message_log.whatsapp_message_log import get_conversation

messages = get_conversation(contact="+1234567890")
```

### Start Campaign

```python
from whatsapp.whatsapp.doctype.whatsapp_campaign.whatsapp_campaign import start_campaign

start_campaign(campaign_name="CAMP-0001")
```

## Rate Limiting

WhatsApp has strict rate limits. This app implements:

1. **Connection-level Limits**: Set daily and monthly limits per connection
2. **Campaign Rate Control**: Configure messages per minute
3. **Automatic Counters**: Daily and monthly counters reset automatically
4. **Queue Management**: Bull queue with Redis for reliable delivery

**Recommended Limits:**
- Daily: 1,000 messages
- Monthly: 30,000 messages
- Sending Rate: 10-20 messages/minute

## Troubleshooting

### Connection Issues

**Problem**: QR code not appearing
- Check Node.js service is running: `pm2 status`
- Check logs: `pm2 logs whatsapp-service`
- Verify Redis is running: `redis-cli ping`

**Problem**: Connection keeps disconnecting
- Check internet connectivity
- Verify phone has WhatsApp installed and active
- Check Node.js service logs for errors

### Message Sending Issues

**Problem**: Messages stuck in "Queued" status
- Check Redis connection
- Verify Node.js service is processing queue
- Check rate limits haven't been exceeded

**Problem**: Messages failing
- Verify recipient phone number format
- Check connection status
- Review error messages in Message Log

### Performance Issues

**Problem**: Slow campaign sending
- Increase Redis memory
- Optimize segment filters
- Reduce sending rate if getting rate limited

## Development

### Running Tests

```bash
cd ~/frappe-bench
bench --site your-site.local run-tests --app whatsapp
```

### Enable Debug Logging

In `.env`:
```env
LOG_LEVEL=debug
```

### Database Migrations

After modifying DocTypes:
```bash
bench --site your-site.local migrate
```

## Security Considerations

1. **Authentication Data**: Stored in `auth_info_baileys` folder - keep secure
2. **API Access**: Use Frappe's built-in authentication
3. **Rate Limiting**: Prevents WhatsApp account bans
4. **Opt-in Compliance**: Always get user consent before messaging
5. **Data Privacy**: Handle contact data per GDPR/privacy laws

## License

MIT License - See LICENSE file

## Support

For issues and questions:
- GitHub Issues: [your-repo/issues]
- Documentation: [your-docs-url]
- Email: whatsapp@inia.co

## Credits

- Built with [Frappe Framework](https://frappeframework.com)
- WhatsApp integration via [@whiskeysockets/baileys](https://github.com/WhiskeySockets/Baileys)
- Message queue powered by [Bull](https://github.com/OptimalBits/bull)
