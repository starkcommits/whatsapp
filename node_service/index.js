const makeWASocket = require('@whiskeysockets/baileys').default;
const { useMultiFileAuthState, DisconnectReason, getContentType, downloadMediaMessage } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const express = require('express');
const { Server } = require('socket.io');
const http = require('http');
const axios = require('axios');
const Bull = require('bull');
const NodeCache = require('node-cache');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

app.use(express.json());

// Configuration
const PORT = process.env.NODE_SERVICE_PORT || 3000;
const FRAPPE_SITE_URL = process.env.FRAPPE_SITE_URL || 'http://localhost:8000';
const AUTH_FOLDER = process.env.AUTH_FOLDER || './auth_info_baileys';

// Store active connections
const connections = new Map();
const groupCache = new NodeCache({ stdTTL: 300, useClones: false });

// Message queue
const messageQueue = new Bull('whatsapp-messages', {
    redis: {
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379
    }
});

// Logger
const logger = pino({ level: process.env.LOG_LEVEL || 'info' });

/**
 * Connect to WhatsApp
 */
async function connectToWhatsApp(connectionId, config) {
    try {
        const authFolder = `${AUTH_FOLDER}/${connectionId}`;
        const { state, saveCreds } = await useMultiFileAuthState(authFolder);

        const sock = makeWASocket({
            auth: state,
            printQRInTerminal: config.connection_method === 'QR Code',
            logger: pino({ level: 'silent' }),
            browser: [config.browser_name || 'Chrome', config.browser_version || 'Desktop', '1.0.0'],
            markOnlineOnConnect: config.mark_online_on_connect || false,
            syncFullHistory: config.sync_full_history || true,
            getMessage: async (key) => {
                // Implement message retrieval from Frappe
                return { conversation: 'Hello' };
            },
            cachedGroupMetadata: async (jid) => groupCache.get(jid)
        });

        // Store connection
        connections.set(connectionId, sock);

        // Handle connection updates
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr && config.connection_method === 'QR Code') {
                // Send QR code to Frappe
                qrcode.generate(qr, { small: true });
                await notifyFrappe(connectionId, 'qr_code', { qr });
            }

            if (connection === 'close') {
                const shouldReconnect = (lastDisconnect?.error instanceof Boom) &&
                    lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut;

                logger.info(`Connection closed for ${connectionId}, reconnecting: ${shouldReconnect}`);

                if (shouldReconnect) {
                    setTimeout(() => connectToWhatsApp(connectionId, config), 5000);
                } else {
                    connections.delete(connectionId);
                    await updateConnectionStatus(connectionId, 'Disconnected');
                }
            } else if (connection === 'open') {
                logger.info(`Connection opened for ${connectionId}`);
                await updateConnectionStatus(connectionId, 'Connected');
            }
        });

        // Handle credentials update
        sock.ev.on('creds.update', saveCreds);

        // Handle incoming messages
        sock.ev.on('messages.upsert', async ({ messages, type }) => {
            for (const msg of messages) {
                if (!msg.message) continue;

                const messageType = getContentType(msg.message);
                const from = msg.key.remoteJid;

                logger.info(`Received message from ${from}, type: ${messageType}`);

                // Save message to Frappe
                await saveIncomingMessage(connectionId, msg, messageType);

                // Handle auto-replies (to be implemented)
                // await handleAutoReply(connectionId, from, msg);
            }
        });

        // Handle message status updates
        sock.ev.on('messages.update', async (updates) => {
            for (const update of updates) {
                const { key, update: msgUpdate } = update;

                if (msgUpdate.status) {
                    await updateMessageStatus(key.id, msgUpdate.status);
                }
            }
        });

        // Handle group metadata updates
        sock.ev.on('groups.update', async ([event]) => {
            const metadata = await sock.groupMetadata(event.id);
            groupCache.set(event.id, metadata);
        });

        // Request pairing code if needed
        if (!state.creds.registered && config.connection_method === 'Pairing Code') {
            const code = await sock.requestPairingCode(config.phone_number);
            logger.info(`Pairing code for ${connectionId}: ${code}`);
            await notifyFrappe(connectionId, 'pairing_code', { code });
            return { pairing_code: code };
        }

        return { success: true };

    } catch (error) {
        logger.error(`Error connecting ${connectionId}:`, error);
        await updateConnectionStatus(connectionId, 'Failed');
        throw error;
    }
}

/**
 * Send message
 */
async function sendMessage(connectionId, recipient, message) {
    try {
        const sock = connections.get(connectionId);
        if (!sock) {
            throw new Error('Connection not found');
        }

        // Format recipient JID
        const jid = recipient.includes('@') ? recipient : `${recipient}@s.whatsapp.net`;

        // Send message
        const result = await sock.sendMessage(jid, message);

        logger.info(`Message sent to ${jid} from ${connectionId}`);
        return result;

    } catch (error) {
        logger.error(`Error sending message:`, error);
        throw error;
    }
}

/**
 * Notify Frappe about events
 */
async function notifyFrappe(connectionId, event, data) {
    try {
        await axios.post(`${FRAPPE_SITE_URL}/api/method/whatsapp.api.webhook_handler.handle_event`, {
            connection_id: connectionId,
            event: event,
            data: data
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        logger.error('Error notifying Frappe:', error.message);
    }
}

/**
 * Update connection status in Frappe
 */
async function updateConnectionStatus(connectionId, status) {
    try {
        await axios.post(`${FRAPPE_SITE_URL}/api/method/whatsapp.api.webhook_handler.update_connection_status`, {
            connection_id: connectionId,
            status: status
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        logger.error('Error updating connection status:', error.message);
    }
}

/**
 * Save incoming message to Frappe
 */
async function saveIncomingMessage(connectionId, msg, messageType) {
    try {
        const content = msg.message.conversation ||
            msg.message.extendedTextMessage?.text ||
            msg.message.imageMessage?.caption ||
            '';

        await axios.post(`${FRAPPE_SITE_URL}/api/method/whatsapp.api.webhook_handler.save_incoming_message`, {
            connection_id: connectionId,
            from: msg.key.remoteJid,
            message_id: msg.key.id,
            message_type: messageType,
            content: content,
            timestamp: msg.messageTimestamp
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        logger.error('Error saving incoming message:', error.message);
    }
}

/**
 * Update message status in Frappe
 */
async function updateMessageStatus(messageId, status) {
    try {
        const statusMap = {
            1: 'Sent',
            2: 'Delivered',
            3: 'Read'
        };

        await axios.post(`${FRAPPE_SITE_URL}/api/method/whatsapp.whatsapp.doctype.whatsapp_message_log.whatsapp_message_log.update_message_status`, {
            message_id: messageId,
            status: statusMap[status] || 'Sent'
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        logger.error('Error updating message status:', error.message);
    }
}

// Message queue processor
messageQueue.process(async (job) => {
    const { connection_id, message_log_id, recipient, message } = job.data;

    try {
        const result = await sendMessage(connection_id, recipient, message);

        // Update message log in Frappe
        await axios.post(`${FRAPPE_SITE_URL}/api/method/whatsapp.whatsapp.doctype.whatsapp_message_log.whatsapp_message_log.update_message_status`, {
            message_log_id: message_log_id,
            status: 'Sent',
            message_id: result.key.id
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });

        return { success: true, message_id: result.key.id };

    } catch (error) {
        logger.error('Error processing message:', error);

        // Mark as failed in Frappe
        await axios.post(`${FRAPPE_SITE_URL}/api/method/whatsapp.whatsapp.doctype.whatsapp_message_log.whatsapp_message_log.update_message_status`, {
            message_log_id: message_log_id,
            status: 'Failed',
            error_message: error.message
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });

        throw error;
    }
});

// API Routes
app.post('/api/connect', async (req, res) => {
    try {
        const { connection_id, phone_number, connection_method, browser_name, browser_version, mark_online_on_connect, sync_full_history } = req.body;

        const result = await connectToWhatsApp(connection_id, {
            phone_number,
            connection_method,
            browser_name,
            browser_version,
            mark_online_on_connect,
            sync_full_history
        });

        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/disconnect', async (req, res) => {
    try {
        const { connection_id } = req.body;

        const sock = connections.get(connection_id);
        if (sock) {
            await sock.logout();
            connections.delete(connection_id);
        }

        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/queue-message', async (req, res) => {
    try {
        const { connection_id, message_log_id, recipient, message, campaign_id } = req.body;

        // Add to queue
        await messageQueue.add({
            connection_id,
            message_log_id,
            recipient,
            message,
            campaign_id
        }, {
            attempts: 3,
            backoff: {
                type: 'exponential',
                delay: 2000
            }
        });

        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/status', (req, res) => {
    res.json({
        active_connections: connections.size,
        queue_waiting: messageQueue.getWaitingCount(),
        queue_active: messageQueue.getActiveCount()
    });
});

// Socket.IO for real-time updates
io.on('connection', (socket) => {
    logger.info('Client connected to Socket.IO');

    socket.on('disconnect', () => {
        logger.info('Client disconnected from Socket.IO');
    });
});

// Start server
server.listen(PORT, () => {
    logger.info(`WhatsApp Baileys service running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    logger.info('SIGTERM received, closing connections...');
    for (const [id, sock] of connections) {
        await sock.logout();
    }
    await messageQueue.close();
    server.close();
    process.exit(0);
});
