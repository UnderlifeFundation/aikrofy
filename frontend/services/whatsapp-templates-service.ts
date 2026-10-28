import apiClient from '@/lib/api-client';

export interface WhatsAppTemplateItem {
  id: number;
  company_id: number;
  meta_template_id?: string;
  name: string;
  category: 'MARKETING' | 'UTILITY' | 'AUTHENTICATION';
  language: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'PAUSED' | 'DRAFT';
  components: any[];
  rejected_reason?: string;
  total_sent: number;
  total_delivered: number;
  total_read: number;
  total_replied: number;
  conversion_rate: number;
  ai_performance_score: number;
  ai_suggestions?: any;
  created_at?: string;
  updated_at?: string;
}

export async function getWhatsAppTemplates(): Promise<WhatsAppTemplateItem[]> {
  const res = await apiClient.get('/whatsapp-templates/');
  return res.data?.templates || [];
}

export async function syncWhatsAppTemplates(): Promise<WhatsAppTemplateItem[]> {
  const res = await apiClient.post('/whatsapp-templates/sync', {});
  return res.data?.templates || [];
}

export async function createWhatsAppTemplate(payload: any): Promise<any> {
  const res = await apiClient.post('/whatsapp-templates/create', payload);
  return res.data;
}

export async function generateAITemplate(goal: string, targetAudience: string): Promise<any> {
  const res = await apiClient.post('/whatsapp-templates/generate-ai', {
    goal,
    target_audience: targetAudience,
  });
  return res.data?.suggestion || null;
}

export async function updateWhatsAppTemplate(id: number, payload: any): Promise<any> {
  const res = await apiClient.put(`/whatsapp-templates/${id}`, payload);
  return res.data;
}

export async function deleteWhatsAppTemplate(id: number): Promise<boolean> {
  const res = await apiClient.delete(`/whatsapp-templates/${id}`);
  return res.data?.success || false;
}
