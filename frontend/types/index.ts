// API Response Types - Mapped 1:1 from Backend Models

// ========================
// Auth
// ========================
export interface User {
    id: number;
    email: string;
    name: string;
    role: 'admin' | 'super_admin' | 'manager' | 'employee' | 'agency';
    /** True only for the account that originally registered the company (root account). */
    is_company_owner: boolean;
    company_id: number | null;
    is_active: boolean;
    is_beta_approved?: boolean;
    has_hardware_gps?: boolean;
    location_consent?: string;
    company_name?: string;
    tax_id?: string;
    phone?: string;
    created_at: string | null;
    last_login: string | null;
    company?: Company | null;
}

/** Context returned by /api/auth/me — drives conditional UI rendering. */
export interface PermissionsContext {
    /** True if the logged-in user is the founding account of the company. */
    is_company_owner: boolean;
    /** True if this user can toggle has_web_access on employee records. */
    can_grant_web_access: boolean;
    /** True if this user can create/delete admin-level accounts. */
    can_manage_admins: boolean;
    /** True for any ADMIN (owner or delegated) and SUPER_ADMINs. */
    is_admin_or_above: boolean;
    /** Linked employee profile, if the user is also an employee. */
    employee_profile: Record<string, unknown> | null;
    /** Resolved RBAC permission matrix (if employee). */
    effective_permissions: Record<string, unknown> | null;
}

export interface Company {
    id: number;
    name: string;
    email: string;
    phone: string | null;
    tax_id?: string | null;
    country: string | null;
    city: string | null;
    language: string;
    subscription_tier: string;
    subscription_active: boolean;
    is_courtesy: boolean;
    is_demo: boolean;
    demo_expires_at: string | null;
    credit_balance: number;
    created_at: string;
    widget_id?: string | null;
    user_email?: string; // For admin list
    user_name?: string;  // For admin list
    plan_name?: string | null;
    initial_setup_completed?: boolean;
    trial_activated?: boolean;
    feedback_submitted?: boolean;
    is_in_trial?: boolean;
}

// No longer using legacy alias

export interface AuthResponse {
    data: {
        user: User;
        company?: Company;
        access_token: string;
        refresh_token: string;
    };
}

export interface MeResponse {
    data: {
        user: User;
        company?: Company;
        permissions_context?: PermissionsContext;
    };
}


// ========================
// Agents
// ========================
export interface AgentFeature {
    id: number;
    name: string;
    label: string;
    category: string;
    description: string;
    is_enabled: boolean;
    order: number;
}

export interface AgentConfig {
    id: number;
    name: string;
    description: string | null;
    agent_type?: string;
    tone: string;
    objective: string;
    gender?: string;
    priority?: number;
    system_prompt: string | null;
    is_active: boolean;
    features: AgentFeature[];
}

// ========================
// CRM (Leads & Customers)
// ========================
export interface Lead {
    id: number;
    company_id: number;
    first_name: string | null;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    source: string;
    status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
    score: number;
    metadata?: Record<string, any> | null;
    tags: string[];
    notes: string | null;
    is_ai_active?: boolean;
    created_at: string;
    updated_at: string;
}

export interface Customer {
    id: number;
    company_id: number;
    first_name: string;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    status: string;
    ident_number?: string | null;
    city?: string | null;
    country?: string | null;
    is_ai_active?: boolean;
    created_at: string;
}

export interface Note {
    id: number;
    company_id: number;
    lead_id: number | null;
    customer_id: number | null;
    content: string;
    author_id: number | null;
    author_name: string;
    created_at: string;
    updated_at: string;
}

// ========================
// Wellness
// ========================
export interface WellnessEvaluation {
    id: number;
    company_id: number;
    lead_id: number | null;
    customer_id: number | null;
    age: number | null;
    gender: string | null;
    height_cm: number | null;
    weight_kg: number | null;
    bmi: number | null;
    energy_level: number | null;
    primary_goal: string | null;
    diagnosis: string | null;
    recommendations: string | null;
    pdf_report_path: string | null;
    created_at: string;
}

export interface Document {
    id: number;
    company_id: number;
    filename: string;
    original_filename: string;
    file_type: string;
    file_size: number | null;
    title: string | null;
    description: string | null;
    chunk_count: number;
    status: 'pending' | 'processing' | 'indexed' | 'error';
    error_message: string | null;
    doc_metadata: Record<string, any>;
    uploaded_at: string;
    processed_at: string | null;
}

// ========================
// Channels
// ========================
export interface Channel {
    id: number;
    company_id: number;
    type: 'whatsapp' | 'telegram' | 'email' | 'web' | 'webchat' | 'voice' | 'sms';
    channel_type: 'whatsapp' | 'telegram' | 'email' | 'web' | 'webchat' | 'voice' | 'sms';
    name: string;
    status: 'active' | 'inactive' | 'error' | 'connected' | 'disconnected' | 'connecting';
    status_message?: string | null;
    credentials?: Record<string, any>;
    config?: Record<string, unknown>;
    created_at: string;
}

// ========================
// Conversations & Omnichannel
// ========================
export interface Message {
    id: number;
    conversation_id: number;
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    channel?: string | null;
    media_url?: string | null;
    media_type?: string | null;
    tool_calls?: any[];
    created_at: string;
}

export interface Conversation {
    id: number;
    company_id: number;
    customer_id?: number | null;
    type: 'customer' | 'employee' | 'admin' | 'internal';
    contact_name?: string | null;
    contact_phone?: string | null;
    contact_email?: string | null;
    channel: string;
    conv_metadata?: Record<string, any>;
    tags?: string[];
    is_active: boolean;
    is_resolved: boolean;
    handover_status?: 'bot_active' | 'human_taken' | 'human_listening' | 'resolved';
    assigned_user_id?: number | null;
    handover_summary?: string | null;
    sentiment_score?: number | null;
    lead_score?: number | null;
    started_at?: string | null;
    last_message_at?: string | null;
    message_count?: number;
    messages?: Message[];
    created_at?: string;
}

export interface CompanyAgentGraph {
    id: number;
    company_id: number;
    name: string;
    description?: string | null;
    canvas_data: Record<string, any>;
    compiled_spec: Record<string, any>;
    is_published: boolean;
    is_active: boolean;
    version: number;
    created_at?: string;
}

export interface DynamicAction {
    id: number;
    company_id: number;
    name: string;
    display_name: string;
    description: string;
    endpoint_url: string;
    http_method: string;
    auth_type: string;
    auth_config?: Record<string, any>;
    parameters_schema?: any[];
    headers?: Record<string, any>;
    response_path?: string | null;
    is_active: boolean;
    created_at?: string;
}

export interface TrustGuardrail {
    id: number;
    company_id: number;
    name: string;
    guardrail_type: string;
    action: string;
    rules: Record<string, any>;
    is_active: boolean;
    created_at?: string;
}

// ========================
// Unified Identity (360)
// ========================
export interface UnifiedContact {
    lead: Lead | null;
    customer: Customer | null;
    conversations: Conversation[];
    appointments: Appointment[];
    evaluations: WellnessEvaluation[];
    notes: Note[];
}

export interface Appointment {
    id: number;
    title: string;
    start_time: string;
    end_time: string;
    status: string;
    notes: string | null;
}

// ========================
// Admin / Plans
// ========================
export interface Plan {
    id: number;
    name: string;
    description: string | null;
    price_monthly: number;
    price_annual: number;
    currency: string;
    features: Record<string, unknown> | null;
    is_active: boolean;
    is_default: boolean;
    external_plan_id: string | null;
    external_plan_token: string | null;
}

export interface Subscription {
    id: number;
    company_id: number;
    plan_id: number;
    status: 'active' | 'trial' | 'past_due' | 'cancelled' | 'courtesy';
    interval: 'monthly' | 'annual';
    created_at: string;
    plan?: Plan;
}

export interface BetaLead {
    id: number;
    contact_name: string;
    role_in_company: string;
    email: string;
    phone: string;
    company_name: string;
    industry: string;
    employee_count: string;
    products_services: string | null;
    ai_experience: string | null;
    ai_results_satisfaction: string | null;
    ai_expectations: string | null;
    additional_notes: string | null;
    status: 'pending' | 'approved' | 'rejected';
    credits_granted: number;
    created_at: string;
    approved_at: string | null;
    created_user_id: number | null;
    created_company_id: number | null;
}

export interface PlatformConfig {
    enable_failover: boolean;
    default_llm_provider: string;
    default_llm_model: string;
    global_rag_enabled: boolean;
    global_rag_namespace: string;
    maintenance_mode: boolean;
    beta_mode: boolean;
    max_agents_per_company: number;
    max_documents_per_company: number;
    platform_company_id: number | null;
}

export interface PlatformMetrics {
    total_companies: number;
    active_subscriptions: number;
    total_leads: number;
    total_customers: number;
    total_conversations: number;
    total_messages: number;
    mrr: number;
}

export interface CompanyMetrics {
    total_leads: number;
    qualified_leads: number;
    total_customers: number;
    messages_today: number;
    active_conversations: number;
    conversion_rate: number;
}

// ========================
// Pagination
// ========================
export interface PaginatedResponse<T> {
    data: T[];
    pagination: {
        page: number;
        per_page: number;
        total: number;
        pages: number;
    };
}

// Generic API Response
export interface ApiResponse<T> {
    data: T;
    error?: string;
}
