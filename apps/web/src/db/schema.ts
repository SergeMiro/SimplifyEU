/**
 * SimplifyEU Drizzle schema (pg-core).
 *
 * Mirrors db/migrations/0001_app_schema.sql — the single source of truth for the
 * Phase 2 plain-PostgreSQL migration off Supabase. Keep the two in sync.
 *
 * Notes:
 *  - `users.id` is self-owned (defaultRandom) now; Better Auth linkage is Phase 3.
 *  - The invoice-detector table is `detectorInvoices` (SQL: detector_invoices) to
 *    avoid clashing with the core billing `invoices` table.
 *  - RLS / policies are deferred to Phase 5 and are not represented here.
 */

import { sql } from "drizzle-orm";
import {
  bigint,
  boolean,
  date,
  doublePrecision,
  foreignKey,
  index,
  inet,
  integer,
  jsonb,
  numeric,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
  varchar,
} from "drizzle-orm/pg-core";

// Better Auth tables (user/session/account/verification). Re-exported so the
// drizzle adapter (src/lib/auth.ts) and the db client see them. See ./auth-schema.
export * from "./auth-schema";

// =============================================================================
// Enums
// =============================================================================

export const accountType = pgEnum("account_type", ["personal", "company"]);

export const apiKeyType = pgEnum("api_key_type", ["standard", "admin", "read-only"]);

export const apiKeyStatus = pgEnum("api_key_status", ["active", "revoked", "expired"]);

export const auditAction = pgEnum("audit_action", [
  "account_created", "account_updated", "account_deleted",
  "user_invited", "user_removed", "role_changed",
  "subscription_created", "subscription_updated", "subscription_canceled",
  "invoice_created", "invoice_sent", "invoice_paid", "invoice_voided",
  "api_key_created", "api_key_revoked",
  "service_added", "service_removed", "service_updated",
  "settings_updated", "password_changed", "email_changed",
  "login_success", "login_failed", "logout",
  "webhook_triggered", "webhook_failed",
]);

export const notificationType = pgEnum("notification_type", [
  "invoice_created", "invoice_paid", "invoice_overdue",
  "subscription_created", "subscription_renewed", "subscription_canceled", "subscription_trial_ending",
  "payment_succeeded", "payment_failed", "payment_method_expiring",
  "account_invitation", "account_role_changed",
  "service_added", "service_removed",
  "api_key_created", "api_key_expiring", "api_key_revoked",
  "system_announcement", "security_alert",
]);

export const notificationStatus = pgEnum("notification_status", ["unread", "read", "archived"]);

export const webhookStatus = pgEnum("webhook_status", ["pending", "success", "failed", "retrying"]);

// =============================================================================
// Core tables (billing / accounts)
// =============================================================================

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  fullName: text("full_name"),
  avatarUrl: text("avatar_url"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  idIdx: index("idx_users_id").on(t.id),
}));

export const accounts = pgTable("accounts", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: text("name").notNull(),
  type: accountType("type").notNull(),
  ownerId: uuid("owner_id").notNull().references(() => users.id, { onDelete: "restrict" }),
  stripeCustomerId: text("stripe_customer_id").unique(),
  vatId: text("vat_id"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  ownerIdx: index("idx_accounts_owner_id").on(t.ownerId),
  stripeIdx: index("idx_accounts_stripe_customer").on(t.stripeCustomerId),
}));

export const memberships = pgTable("memberships", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  userId: uuid("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  role: text("role").notNull().default("member"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  accountIdx: index("idx_memberships_account_id").on(t.accountId),
  userIdx: index("idx_memberships_user_id").on(t.userId),
  roleIdx: index("idx_memberships_role").on(t.role),
  accountUserUq: uniqueIndex("memberships_account_id_user_id_key").on(t.accountId, t.userId),
}));

export const subscriptions = pgTable("subscriptions", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  stripeSubscriptionId: text("stripe_subscription_id").unique(),
  plan: text("plan").notNull().default("free"),
  status: text("status").notNull().default("active"),
  currentPeriodStart: timestamp("current_period_start", { withTimezone: true }).notNull().defaultNow(),
  currentPeriodEnd: timestamp("current_period_end", { withTimezone: true }).notNull().defaultNow(),
  cancelAt: timestamp("cancel_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  accountIdx: index("idx_subscriptions_account_id").on(t.accountId),
  statusIdx: index("idx_subscriptions_status").on(t.status),
  stripeIdx: index("idx_subscriptions_stripe").on(t.stripeSubscriptionId),
}));

export const invoices = pgTable("invoices", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  stripeInvoiceId: text("stripe_invoice_id").unique(),
  amount: numeric("amount").notNull().default("0"),
  currency: text("currency").notNull().default("eur"),
  status: text("status").notNull().default("draft"),
  pdfUrl: text("pdf_url"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  accountIdx: index("idx_invoices_account_id").on(t.accountId),
  statusIdx: index("idx_invoices_status").on(t.status),
  stripeIdx: index("idx_invoices_stripe").on(t.stripeInvoiceId),
  createdIdx: index("idx_invoices_created_at").on(t.createdAt.desc()),
}));

export const services = pgTable("services", {
  id: uuid("id").primaryKey().defaultRandom(),
  slug: text("slug").notNull().unique(),
  name: text("name").notNull(),
  description: text("description"),
  icon: text("icon"),
  pricingType: text("pricing_type").notNull().default("included"),
  addonPrice: numeric("addon_price"),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  slugIdx: index("idx_services_slug").on(t.slug),
  activeIdx: index("idx_services_active").on(t.isActive),
}));

export const apiKeys = pgTable("api_keys", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  prefix: text("prefix").notNull(),
  hashedKey: text("hashed_key").notNull(),
  type: apiKeyType("type").notNull().default("standard"),
  status: apiKeyStatus("status").notNull().default("active"),
  lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  createdBy: uuid("created_by").references(() => users.id),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  accountIdx: index("idx_api_keys_account_id").on(t.accountId),
  prefixIdx: index("idx_api_keys_prefix").on(t.prefix),
  statusIdx: index("idx_api_keys_status").on(t.status),
  expiresIdx: index("idx_api_keys_expires_at").on(t.expiresAt).where(sql`expires_at IS NOT NULL`),
}));

export const auditLogs = pgTable("audit_logs", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  userId: uuid("user_id").references(() => users.id, { onDelete: "set null" }),
  action: auditAction("action").notNull(),
  entityType: text("entity_type").notNull(),
  entityId: uuid("entity_id"),
  oldData: jsonb("old_data"),
  newData: jsonb("new_data"),
  ipAddress: inet("ip_address"),
  userAgent: text("user_agent"),
  metadata: jsonb("metadata").default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  accountIdx: index("idx_audit_logs_account_id").on(t.accountId),
  userIdx: index("idx_audit_logs_user_id").on(t.userId),
  actionIdx: index("idx_audit_logs_action").on(t.action),
  entityIdx: index("idx_audit_logs_entity").on(t.entityType, t.entityId),
  createdIdx: index("idx_audit_logs_created_at").on(t.createdAt),
  accountCreatedIdx: index("idx_audit_logs_account_created").on(t.accountId, t.createdAt.desc()),
}));

export const notifications = pgTable("notifications", {
  id: uuid("id").primaryKey().defaultRandom(),
  userId: uuid("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  accountId: uuid("account_id").references(() => accounts.id, { onDelete: "set null" }),
  type: notificationType("type").notNull(),
  title: text("title").notNull(),
  message: text("message").notNull(),
  data: jsonb("data").default({}),
  status: notificationStatus("status").notNull().default("unread"),
  readAt: timestamp("read_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  userIdx: index("idx_notifications_user_id").on(t.userId),
  accountIdx: index("idx_notifications_account_id").on(t.accountId),
  typeIdx: index("idx_notifications_type").on(t.type),
  statusIdx: index("idx_notifications_status").on(t.status),
  createdIdx: index("idx_notifications_created_at").on(t.createdAt.desc()),
  userUnreadIdx: index("idx_notifications_user_unread").on(t.userId, t.status).where(sql`status = 'unread'`),
}));

export const webhookLogs = pgTable("webhook_logs", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  webhookId: uuid("webhook_id").notNull(),
  eventType: text("event_type").notNull(),
  payload: jsonb("payload").notNull(),
  url: text("url").notNull(),
  status: webhookStatus("status").notNull().default("pending"),
  responseStatus: integer("response_status"),
  responseBody: text("response_body"),
  errorMessage: text("error_message"),
  attemptCount: integer("attempt_count").notNull().default(1),
  nextRetryAt: timestamp("next_retry_at", { withTimezone: true }),
  lastAttemptAt: timestamp("last_attempt_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  accountIdx: index("idx_webhook_logs_account_id").on(t.accountId),
  webhookIdx: index("idx_webhook_logs_webhook_id").on(t.webhookId),
  statusIdx: index("idx_webhook_logs_status").on(t.status),
  eventIdx: index("idx_webhook_logs_event_type").on(t.eventType),
  nextRetryIdx: index("idx_webhook_logs_next_retry").on(t.nextRetryAt).where(sql`status = 'retrying'`),
  createdIdx: index("idx_webhook_logs_created_at").on(t.createdAt.desc()),
}));

export const apiUsage = pgTable("api_usage", {
  id: uuid("id").primaryKey().defaultRandom(),
  apiKeyId: uuid("api_key_id").notNull().references(() => apiKeys.id, { onDelete: "cascade" }),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  endpoint: text("endpoint").notNull(),
  method: text("method").notNull(),
  requestCount: integer("request_count").notNull().default(1),
  bandwidthBytes: bigint("bandwidth_bytes", { mode: "number" }).notNull().default(0),
  periodStart: timestamp("period_start", { withTimezone: true }).notNull().default(sql`date_trunc('day', now())`),
  periodEnd: timestamp("period_end", { withTimezone: true }).notNull().default(sql`date_trunc('day', now()) + INTERVAL '1 day'`),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  apiKeyIdx: index("idx_api_usage_api_key_id").on(t.apiKeyId),
  accountIdx: index("idx_api_usage_account_id").on(t.accountId),
  periodIdx: index("idx_api_usage_period").on(t.periodStart, t.periodEnd),
  keyPeriodIdx: index("idx_api_usage_key_period").on(t.apiKeyId, t.periodStart.desc()),
  uniqueIdx: uniqueIndex("idx_api_usage_unique").on(t.apiKeyId, t.periodStart, t.endpoint),
}));

// =============================================================================
// Subscription analyzer
// =============================================================================

export const analyses = pgTable("analyses", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: uuid("account_id").notNull().references(() => accounts.id, { onDelete: "cascade" }),
  userId: uuid("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  status: text("status").notNull(),
  sourceType: text("source_type").notNull().default("csv"),
  filename: text("filename"),
  fileUrl: text("file_url"),
  totalTransactions: integer("total_transactions"),
  subscriptionsFound: integer("subscriptions_found").default(0),
  potentialSavingsEur: numeric("potential_savings_eur", { precision: 10, scale: 2 }).default("0"),
  reportUrl: text("report_url"),
  errorMessage: text("error_message"),
  startedAt: timestamp("started_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_analyses_account").on(t.accountId),
  statusIdx: index("idx_analyses_status").on(t.status),
}));

export const analysisItems = pgTable("analysis_items", {
  id: uuid("id").primaryKey().defaultRandom(),
  analysisId: uuid("analysis_id").notNull().references(() => analyses.id, { onDelete: "cascade" }),
  merchantDescriptor: text("merchant_descriptor").notNull(),
  merchantName: text("merchant_name"),
  category: text("category"),
  amountAvg: numeric("amount_avg", { precision: 10, scale: 2 }).notNull(),
  amountMin: numeric("amount_min", { precision: 10, scale: 2 }),
  amountMax: numeric("amount_max", { precision: 10, scale: 2 }),
  currency: text("currency").default("EUR"),
  frequency: text("frequency"),
  occurrences: integer("occurrences").notNull(),
  firstSeen: date("first_seen").notNull(),
  lastSeen: date("last_seen").notNull(),
  confidenceScore: numeric("confidence_score", { precision: 3, scale: 2 }),
  isSubscription: boolean("is_subscription").default(false),
  tags: jsonb("tags").default([]),
  recommendation: text("recommendation"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  analysisIdx: index("idx_items_analysis").on(t.analysisId),
  confidenceIdx: index("idx_items_confidence").on(t.confidenceScore.desc()),
}));

// =============================================================================
// Invoice duplicate detector (source table name `invoices` -> `detector_invoices`)
// =============================================================================

export const detectorInvoices = pgTable("detector_invoices", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: varchar("account_id", { length: 100 }).notNull(),
  filename: varchar("filename", { length: 500 }).notNull(),
  fileHash: varchar("file_hash", { length: 64 }).notNull(),
  invoiceNumber: varchar("invoice_number", { length: 100 }),
  vendorName: varchar("vendor_name", { length: 300 }),
  invoiceDate: varchar("invoice_date", { length: 20 }),
  dueDate: varchar("due_date", { length: 20 }),
  totalAmount: numeric("total_amount", { precision: 15, scale: 2 }),
  currency: varchar("currency", { length: 10 }).default("EUR"),
  lineItems: jsonb("line_items").default([]),
  rawText: text("raw_text"),
  ocrUsed: boolean("ocr_used").default(false),
  status: varchar("status", { length: 20 }).default("pending"),
  processingError: text("processing_error"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_invoices_account_id_det").on(t.accountId),
  fileHashIdx: index("idx_invoices_file_hash").on(t.fileHash),
  statusIdx: index("idx_invoices_status_det").on(t.status),
  invoiceNumberIdx: index("idx_invoices_invoice_number").on(t.invoiceNumber),
  vendorIdx: index("idx_invoices_vendor").on(t.vendorName),
}));

export const duplicatePairs = pgTable("duplicate_pairs", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: varchar("account_id", { length: 100 }).notNull(),
  invoiceAId: uuid("invoice_a_id").notNull().references(() => detectorInvoices.id, { onDelete: "cascade" }),
  invoiceBId: uuid("invoice_b_id").notNull().references(() => detectorInvoices.id, { onDelete: "cascade" }),
  similarityScore: numeric("similarity_score", { precision: 6, scale: 4 }).notNull(),
  matchDetails: jsonb("match_details").default({}),
  status: varchar("status", { length: 20 }).default("pending"),
  reviewedBy: varchar("reviewed_by", { length: 100 }),
  reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_dup_account").on(t.accountId),
  statusIdx: index("idx_dup_status").on(t.status),
  scoreIdx: index("idx_dup_score").on(t.similarityScore.desc()),
  pairUq: uniqueIndex("duplicate_pairs_invoice_a_id_invoice_b_id_key").on(t.invoiceAId, t.invoiceBId),
}));

// =============================================================================
// Team reminder bot
// =============================================================================

export const teams = pgTable("teams", {
  id: uuid("id").primaryKey().defaultRandom(),
  slackTeamId: varchar("slack_team_id", { length: 50 }).notNull().unique(),
  name: varchar("name", { length: 200 }).notNull(),
  subscriptionTier: varchar("subscription_tier", { length: 20 }).default("free"),
  remindersCount: integer("reminders_count").default(0),
  maxReminders: integer("max_reminders").default(50),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  slackTeamIdx: index("idx_teams_slack_team_id").on(t.slackTeamId),
}));

export const reminders = pgTable("reminders", {
  id: uuid("id").primaryKey().defaultRandom(),
  teamId: uuid("team_id").notNull().references(() => teams.id, { onDelete: "cascade" }),
  creatorUserId: varchar("creator_user_id", { length: 100 }).notNull(),
  targetUserId: varchar("target_user_id", { length: 100 }).notNull(),
  taskText: text("task_text").notNull(),
  context: text("context"),
  project: varchar("project", { length: 200 }),
  priority: varchar("priority", { length: 20 }).default("medium"),
  remindAt: timestamp("remind_at", { withTimezone: true }).notNull(),
  status: varchar("status", { length: 20 }).default("pending"),
  repeat: varchar("repeat", { length: 20 }),
  parentReminderId: uuid("parent_reminder_id"),
  sentAt: timestamp("sent_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  snoozeCount: integer("snooze_count").default(0),
  retryCount: integer("retry_count").default(0),
  errorMessage: text("error_message"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  // self-reference (parent_reminder_id -> reminders.id ON DELETE SET NULL)
  parentFk: foreignKey({
    columns: [t.parentReminderId],
    foreignColumns: [t.id],
    name: "reminders_parent_reminder_id_fkey",
  }).onDelete("set null"),
  teamIdx: index("idx_reminders_team_id").on(t.teamId),
  statusIdx: index("idx_reminders_status").on(t.status),
  remindAtIdx: index("idx_reminders_remind_at").on(t.remindAt),
  targetUserIdx: index("idx_reminders_target_user").on(t.targetUserId),
  dueIdx: index("idx_reminders_due").on(t.status, t.remindAt).where(sql`status = 'pending'`),
}));

export const contextHistory = pgTable("context_history", {
  id: uuid("id").primaryKey().defaultRandom(),
  teamId: uuid("team_id").notNull().references(() => teams.id, { onDelete: "cascade" }),
  userId: varchar("user_id", { length: 100 }).notNull(),
  eventType: varchar("event_type", { length: 50 }).notNull(),
  eventData: jsonb("event_data").default({}),
  relatedReminderId: uuid("related_reminder_id").references(() => reminders.id, { onDelete: "set null" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  teamUserIdx: index("idx_context_history_team_user").on(t.teamId, t.userId),
  createdIdx: index("idx_context_history_created").on(t.createdAt.desc()),
}));

// =============================================================================
// CrewAI agents service (account_id is a free-form TEXT tenant key, not an FK)
// =============================================================================

export const businessProfiles = pgTable("business_profiles", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull().unique(),
  businessType: text("business_type").notNull(),
  taxRegime: text("tax_regime").notNull().default("micro"),
  declarationFrequency: text("declaration_frequency").notNull().default("monthly"),
  tvaApplicable: boolean("tva_applicable").notNull().default(false),
  siret: text("siret"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_business_profiles_account").on(t.accountId),
}));

export const agentSettings = pgTable("agent_settings", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  agentType: text("agent_type").notNull(),
  status: text("status").notNull().default("disabled"),
  notificationChannels: jsonb("notification_channels").notNull().default(["in_app"]),
  config: jsonb("config").notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_agent_settings_account").on(t.accountId),
  accountTypeIdx: index("idx_agent_settings_account_type").on(t.accountId, t.agentType),
  accountTypeUq: uniqueIndex("agent_settings_account_id_agent_type_key").on(t.accountId, t.agentType),
}));

export const taxObligations = pgTable("tax_obligations", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  obligationType: text("obligation_type").notNull(),
  title: text("title").notNull(),
  description: text("description"),
  deadline: timestamp("deadline", { withTimezone: true }).notNull(),
  status: text("status").notNull().default("pending"),
  draftData: jsonb("draft_data"),
  serviceUrl: text("service_url"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_tax_obligations_account").on(t.accountId),
  deadlineIdx: index("idx_tax_obligations_deadline").on(t.deadline),
  statusIdx: index("idx_tax_obligations_status").on(t.accountId, t.status),
}));

export const financialInsights = pgTable("financial_insights", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  insightType: text("insight_type").notNull(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  severity: text("severity").notNull().default("info"),
  data: jsonb("data").notNull().default({}),
  acknowledged: boolean("acknowledged").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_financial_insights_account").on(t.accountId),
  unackIdx: index("idx_financial_insights_unack").on(t.accountId, t.acknowledged),
}));

export const documentLinks = pgTable("document_links", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  documentId: uuid("document_id").notNull(),
  transactionId: text("transaction_id"),
  matchConfidence: doublePrecision("match_confidence"),
  verified: boolean("verified").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_document_links_account").on(t.accountId),
  documentIdx: index("idx_document_links_document").on(t.documentId),
}));

export const agentExecutionLogs = pgTable("agent_execution_logs", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  agentType: text("agent_type").notNull(),
  flowName: text("flow_name"),
  trigger: text("trigger"),
  status: text("status").notNull().default("running"),
  inputData: jsonb("input_data").notNull().default({}),
  outputData: jsonb("output_data").notNull().default({}),
  errorMessage: text("error_message"),
  startedAt: timestamp("started_at", { withTimezone: true }).defaultNow(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
}, (t) => ({
  accountIdx: index("idx_agent_execution_logs_account").on(t.accountId),
  flowIdx: index("idx_agent_execution_logs_flow").on(t.accountId, t.flowName),
}));

export const agentNotifications = pgTable("agent_notifications", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  title: text("title").notNull(),
  message: text("message").notNull(),
  notificationType: text("notification_type").notNull().default("info"),
  agentType: text("agent_type"),
  actionUrl: text("action_url"),
  read: boolean("read").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_agent_notifications_account").on(t.accountId),
  unreadIdx: index("idx_agent_notifications_unread").on(t.accountId, t.read),
}));

export const weeklyReports = pgTable("weekly_reports", {
  id: uuid("id").primaryKey().defaultRandom(),
  accountId: text("account_id").notNull(),
  periodStart: timestamp("period_start", { withTimezone: true }).notNull(),
  periodEnd: timestamp("period_end", { withTimezone: true }).notNull(),
  summary: text("summary").notNull(),
  highlights: jsonb("highlights").notNull().default([]),
  actionItems: jsonb("action_items").notNull().default([]),
  financialSnapshot: jsonb("financial_snapshot").notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (t) => ({
  accountIdx: index("idx_weekly_reports_account").on(t.accountId),
}));
