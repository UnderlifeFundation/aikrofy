/**
 * Aikrofy Community Edition — Single-Account WhatsApp Middleware
 * Powered by @agenticnucleus/whatsapp-multitenant
 *
 * This lightweight gateway uses the official @agenticnucleus/whatsapp-multitenant
 * NPM library and enforces a strict Single-Account (1 session) lock for
 * self-hosted Community deployments.
 *
 * Copyright (c) 2026 FUNDACIÓN UNDERLIFE & WEBLIFETECH (Jonnathan Peña)
 */
require("dotenv/config");
const express = require("express");
const cors = require("cors");
const { BaileysTransporter, LeadCreate } = require("@agenticnucleus/whatsapp-multitenant");

const PORT = process.env.PORT || 3011;
const SINGLE_TENANT_ID = String(process.env.COMMUNITY_COMPANY_ID || "1");

const app = express();
app.use(cors());
app.use(express.json());

// Initialize transporter from @agenticnucleus/whatsapp-multitenant
const transporter = new BaileysTransporter();
const dbMock = { save: () => Promise.resolve() };
const leadCreator = new LeadCreate([dbMock, transporter]);

/**
 * Helper: Enforces Single-Account lock in Community Edition.
 * Only allows the primary community account (default ID "1") or the first registered company.
 */
function resolveCommunityTenant(requestedCompanyId) {
  const activeSessions = transporter.getAllSessions ? transporter.getAllSessions() : [];
  if (activeSessions.length > 0) {
    const existingId = String(activeSessions[0].companyId);
    if (requestedCompanyId && String(requestedCompanyId) !== existingId) {
      throw new Error(
        `Aikrofy Community Edition is limited to 1 active WhatsApp account (Active ID: ${existingId}). For Multi-Tenant support, upgrade to Aikrofy Cloud / Enterprise.`
      );
    }
    return existingId;
  }
  return String(requestedCompanyId || SINGLE_TENANT_ID);
}

// ── Session Endpoints ─────────────────────────────────────────────────────────

app.post("/session/init", async (req, res) => {
  try {
    const companyId = resolveCommunityTenant(req.body.companyId);
    const forceNew = Boolean(req.body.forceNew);
    const result = await transporter.startSession(companyId, forceNew);
    res.json(result);
  } catch (err) {
    res.status(403).json({ error: err.message, status: "error" });
  }
});

app.get("/session/qr/:companyId", (req, res) => {
  try {
    const companyId = resolveCommunityTenant(req.params.companyId);
    const qrSvg = transporter.getQr(companyId);
    if (!qrSvg) {
      const status = transporter.getStatus(companyId);
      if (status.connected) {
        return res.json({ status: "connected", message: "Session already connected" });
      }
      return res.status(404).json({ error: "QR not available yet" });
    }
    res.setHeader("Content-Type", "image/svg+xml");
    res.send(qrSvg);
  } catch (err) {
    res.status(403).json({ error: err.message });
  }
});

app.get("/session/status/:companyId", (req, res) => {
  try {
    const companyId = resolveCommunityTenant(req.params.companyId);
    const status = transporter.getStatus(companyId);
    res.json({ companyId, ...status });
  } catch (err) {
    res.json({ companyId: req.params.companyId, connected: false, state: "restricted", error: err.message });
  }
});

app.get("/session/status-restore/:companyId", async (req, res) => {
  try {
    const companyId = resolveCommunityTenant(req.params.companyId);
    const status = await transporter.getStatusWithAutoRestore(companyId);
    res.json({ companyId, ...status });
  } catch (err) {
    res.json({ companyId: req.params.companyId, connected: false, state: "restricted", error: err.message });
  }
});

app.post("/session/logout", async (req, res) => {
  try {
    const companyId = resolveCommunityTenant(req.body.companyId);
    await transporter.logout(companyId);
    res.json({ status: "logged_out", companyId });
  } catch (err) {
    res.status(500).json({ error: err.message, status: "error" });
  }
});

app.get("/session/list", (_req, res) => {
  const sessions = transporter.getAllSessions ? transporter.getAllSessions() : [];
  res.json({ mode: "community-single-account", maxAccounts: 1, sessions: sessions.slice(0, 1) });
});

// ── Messaging Endpoints (/lead) ───────────────────────────────────────────────

app.post("/lead", async (req, res) => {
  try {
    const { message, phone } = req.body;
    const companyId = resolveCommunityTenant(req.body.companyId);
    if (!message || !phone) {
      return res.status(400).json({ error: "message and phone are required" });
    }
    const response = await leadCreator.sendMessageAndSave({ message, phone, companyId });
    res.json(response);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/lead/typing", async (req, res) => {
  try {
    const { phone } = req.body;
    const companyId = resolveCommunityTenant(req.body.companyId);
    if (!phone) return res.status(400).json({ error: "phone is required" });
    await leadCreator.sendTyping({ phone, companyId });
    res.json({ status: "ok" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/lead/media", async (req, res) => {
  try {
    const { phone, mediaUrl, mediaType, caption, fileName } = req.body;
    const companyId = resolveCommunityTenant(req.body.companyId);
    if (!phone || !mediaUrl || !mediaType) {
      return res.status(400).json({ error: "missing media parameters" });
    }
    await leadCreator.sendMedia({ phone, companyId, mediaUrl, mediaType, caption, fileName });
    res.json({ status: "ok" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/lead/interactive", async (req, res) => {
  try {
    const { phone, body, title, footer, buttons } = req.body;
    const companyId = resolveCommunityTenant(req.body.companyId);
    const formatted = [
      title ? `*${title}*` : "",
      body || "",
      Array.isArray(buttons) ? buttons.map((b, i) => `${i + 1}. ${b.title || b.text || b}`).join("\n") : "",
      footer ? `_${footer}_` : "",
    ]
      .filter(Boolean)
      .join("\n\n");
    const response = await leadCreator.sendMessageAndSave({ message: formatted, phone, companyId });
    res.json(response);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`🏛️  Aikrofy Community WhatsApp Bridge (Single-Account) running on port ${PORT}`);
  console.log(`📦 Powered by @agenticnucleus/whatsapp-multitenant`);
});
