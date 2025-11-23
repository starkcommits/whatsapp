# WhatsApp Marketing App - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Run Setup Script

```bash
cd ~/frappe-bench/apps/whatsapp
./setup.sh
```

This will:
- Check Node.js and Redis installation
- Install npm dependencies
- Create .env file
- Set up auth folder
- Start Redis if needed

### 2. Configure Environment

Edit `.env`:
```env
FRAPPE_SITE_URL=http://localhost:8000  # Your Frappe site URL
NODE_SERVICE_PORT=3000
REDIS_HOST=localhost
REDIS_PORT=6379
```

Edit `site_config.json` (in your site folder):
```json
{
  "whatsapp_node_service_url": "http://localhost:3000"
}
```

### 3. Start Node.js Service

**Development:**
```bash
npm start
```

**Production (with PM2):**
```bash
npm install -g pm2
pm2 start node_service/index.js --name whatsapp-service
pm2 save
pm2 startup  # Follow instructions to enable on boot
```

### 4. Create Your First Connection

1. Open Frappe: `http://localhost:8000`
2. Go to **WhatsApp > WhatsApp Connection**
3. Click **New**
4. Fill in:
   - **Connection Name**: My WhatsApp
   - **Phone Number**: +1234567890 (with country code)
   - **Connection Method**: QR Code (or Pairing Code)
   - **Daily Message Limit**: 1000
   - **Monthly Message Limit**: 30000
5. **Save**
6. Click **Connect** button
7. **Scan QR code** with WhatsApp on your phone (or enter pairing code)
8. Wait for status to change to "Connected" ✅

### 5. Send Your First Message

**Via UI:**
1. Go to **WhatsApp > WhatsApp Contact**
2. Create a contact with phone number
3. Use **Send Message** button

**Via API:**
```python
import frappe
from whatsapp.whatsapp.api.whatsapp_api import send_message

send_message(
    connection="My WhatsApp",
    recipient="+1234567890",
    message_type="Text",
    content="Hello from Frappe! 👋"
)
```

### 6. Create Your First Campaign

1. **Create Template:**
   - Go to **WhatsApp > WhatsApp Message Template**
   - Name: Welcome Message
   - Content: `Hello {{name}}, welcome to our service!`
   - Save

2. **Create Segment:**
   - Go to **WhatsApp > WhatsApp Contact Segment**
   - Name: All Opted In
   - Filter: `{"opt_in_status": "Opted In"}`
   - Save

3. **Create Campaign:**
   - Go to **WhatsApp > WhatsApp Campaign**
   - Campaign Name: Welcome Campaign
   - Connection: My WhatsApp
   - Target Segment: All Opted In
   - Message Template: Welcome Message
   - Schedule Type: Immediate
   - Sending Rate: 10 (messages/minute)
   - Save
   - Click **Start Campaign** 🚀

## 📊 Monitoring

### Check Service Status
```bash
# Via PM2
pm2 status
pm2 logs whatsapp-service

# Via API
curl http://localhost:3000/api/status
```

### View Campaign Progress
1. Go to **WhatsApp > WhatsApp Campaign**
2. Open your campaign
3. See real-time statistics:
   - Messages Sent
   - Delivered
   - Read
   - Failed
   - Delivery Rate
   - Read Rate

### View Message Logs
Go to **WhatsApp > WhatsApp Message Log** to see all messages

## 🔧 Troubleshooting

### Connection Won't Connect
```bash
# Check Node.js service
pm2 logs whatsapp-service

# Check Redis
redis-cli ping  # Should return PONG

# Restart service
pm2 restart whatsapp-service
```

### Messages Not Sending
1. Check connection status (should be "Connected")
2. Check rate limits not exceeded
3. Verify phone number format (+countrycode number)
4. Check Redis queue: `redis-cli LLEN bull:whatsapp-messages:wait`

### QR Code Not Showing
1. Ensure `printQRInTerminal: true` in connection
2. Check Node.js service logs
3. Try pairing code method instead

## 🎯 Next Steps

1. **Set up Auto-Replies:**
   - Go to **WhatsApp > WhatsApp Auto Reply**
   - Create keyword-based responses

2. **Import Bulk Contacts:**
   ```python
   from whatsapp.whatsapp.doctype.whatsapp_contact.whatsapp_contact import import_contacts
   
   contacts = [
       {"phone_number": "+1234567890", "name": "John", "opt_in_status": "Opted In"},
       {"phone_number": "+0987654321", "name": "Jane", "opt_in_status": "Opted In"}
   ]
   
   import_contacts(contacts)
   ```

3. **Create Advanced Segments:**
   - Use tags for filtering
   - Combine multiple conditions
   - Auto-updating segments

4. **Schedule Campaigns:**
   - Set future send times
   - Create recurring campaigns
   - A/B test different templates

## 📚 Resources

- Full Documentation: See README.md
- API Reference: See README.md#api-reference
- Baileys Documentation: https://whiskeysockets.github.io/
- Frappe Documentation: https://frappeframework.com/docs

## 🆘 Support

- Check logs: `pm2 logs whatsapp-service`
- Enable debug: Set `LOG_LEVEL=debug` in .env
- GitHub Issues: [your-repo]
- Email: whatsapp@inia.co

---

**Happy Messaging! 📱✨**
