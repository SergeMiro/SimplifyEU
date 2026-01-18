import { z } from 'zod';

// Enums
export const AccountType = z.enum(['personal', 'company']);
export type AccountType = z.infer<typeof AccountType>;

export const SubscriptionPlan = z.enum(['free', 'starter', 'pro', 'enterprise']);
export type SubscriptionPlan = z.infer<typeof SubscriptionPlan>;

export const SubscriptionStatus = z.enum(['active', 'canceled', 'past_due', 'trialing']);
export type SubscriptionStatus = z.infer<typeof SubscriptionStatus>;

export const InvoiceStatus = z.enum(['draft', 'open', 'paid', 'void', 'uncollectible']);
export type InvoiceStatus = z.infer<typeof InvoiceStatus>;

export const MembershipRole = z.enum(['owner', 'admin', 'member']);
export type MembershipRole = z.infer<typeof MembershipRole>;

export const ServicePricingType = z.enum(['free', 'included', 'addon']);
export type ServicePricingType = z.infer<typeof ServicePricingType>;

// Database Tables
export const usersSchema = z.object({
  id: z.string().uuid(),
  full_name: z.string().nullable(),
  avatar_url: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type Users = z.infer<typeof usersSchema>;

export const accountsSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  type: AccountType,
  owner_id: z.string().uuid(),
  stripe_customer_id: z.string().nullable(),
  vat_id: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type Accounts = z.infer<typeof accountsSchema>;

export const membershipsSchema = z.object({
  id: z.string().uuid(),
  account_id: z.string().uuid(),
  user_id: z.string().uuid(),
  role: MembershipRole,
  created_at: z.string().datetime(),
});
export type Memberships = z.infer<typeof membershipsSchema>;

export const subscriptionsSchema = z.object({
  id: z.string().uuid(),
  account_id: z.string().uuid(),
  stripe_subscription_id: z.string().nullable(),
  plan: SubscriptionPlan,
  status: SubscriptionStatus,
  current_period_start: z.string().datetime(),
  current_period_end: z.string().datetime(),
  cancel_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
});
export type Subscriptions = z.infer<typeof subscriptionsSchema>;

export const invoicesSchema = z.object({
  id: z.string().uuid(),
  account_id: z.string().uuid(),
  stripe_invoice_id: z.string().nullable(),
  amount: z.number(),
  currency: z.string().default('eur'),
  status: InvoiceStatus,
  pdf_url: z.string().nullable(),
  created_at: z.string().datetime(),
});
export type Invoices = z.infer<typeof invoicesSchema>;

export const servicesSchema = z.object({
  id: z.string().uuid(),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  icon: z.string(),
  pricing_type: ServicePricingType,
  addon_price: z.number().nullable(),
  is_active: z.boolean().default(true),
  created_at: z.string().datetime(),
});
export type Services = z.infer<typeof servicesSchema>;

export const accountServicesSchema = z.object({
  id: z.string().uuid(),
  account_id: z.string().uuid(),
  service_id: z.string().uuid(),
  enabled: z.boolean().default(false),
  settings: z.record(z.unknown()).default({}),
  enabled_at: z.string().datetime().nullable(),
  disabled_at: z.string().datetime().nullable(),
});
export type AccountServices = z.infer<typeof accountServicesSchema>;

export const apiKeysSchema = z.object({
  id: z.string().uuid(),
  account_id: z.string().uuid(),
  service_id: z.string().uuid(),
  key_hash: z.string(),
  key_prefix: z.string(),
  name: z.string(),
  last_used_at: z.string().datetime().nullable(),
  expires_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  revoked_at: z.string().datetime().nullable(),
});
export type ApiKeys = z.infer<typeof apiKeysSchema>;

export const auditLogsSchema = z.object({
  id: z.string().uuid(),
  account_id: z.string().uuid(),
  user_id: z.string().uuid(),
  action: z.string(),
  resource_type: z.string(),
  resource_id: z.string().uuid().nullable(),
  metadata: z.record(z.unknown()).default({}),
  created_at: z.string().datetime(),
});
export type AuditLogs = z.infer<typeof auditLogsSchema>;

// API Request/Response Types
export const CreateAccountInput = z.object({
  name: z.string().min(1),
  type: AccountType,
  vat_id: z.string().nullable().optional(),
});
export type CreateAccountInput = z.infer<typeof CreateAccountInput>;

export const UpdateAccountInput = z.object({
  name: z.string().min(1).optional(),
  vat_id: z.string().nullable().optional(),
});
export type UpdateAccountInput = z.infer<typeof UpdateAccountInput>;

export const CreateServiceInput = z.object({
  slug: z.string().min(1),
  name: z.string().min(1),
  description: z.string(),
  icon: z.string(),
  pricing_type: ServicePricingType,
  addon_price: z.number().nullable().optional(),
});
export type CreateServiceInput = z.infer<typeof CreateServiceInput>;

export const UpdateAccountServiceInput = z.object({
  enabled: z.boolean(),
  settings: z.record(z.unknown()).optional(),
});
export type UpdateAccountServiceInput = z.infer<typeof UpdateAccountServiceInput>;

export const CreateApiKeyInput = z.object({
  service_id: z.string().uuid(),
  name: z.string().min(1),
  expires_at: z.string().datetime().nullable().optional(),
});
export type CreateApiKeyInput = z.infer<typeof CreateApiKeyInput>;

// Pagination
export const PaginationParams = z.object({
  page: z.number().int().positive().default(1),
  limit: z.number().int().positive().max(100).default(20),
});
export type PaginationParams = z.infer<typeof PaginationParams>;

export const PaginatedResponse = z.object({
  data: z.array(z.unknown()),
  total: z.number(),
  page: z.number(),
  limit: z.number(),
  totalPages: z.number(),
});
export type PaginatedResponse<T> = z.infer<typeof PaginatedResponse<T>>;

// Error Types
export const ApiError = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
});
export type ApiError = z.infer<typeof ApiError>;

// Export all schemas as types
export type {
  Users,
  Accounts,
  Memberships,
  Subscriptions,
  Invoices,
  Services,
  AccountServices,
  ApiKeys,
  AuditLogs,
};