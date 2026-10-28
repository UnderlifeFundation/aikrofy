'use client';

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FileText,
  Sparkles,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  TrendingUp,
  Loader2,
  Eye,
  Send,
  MessageSquare,
  Pencil,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import {
  getWhatsAppTemplates,
  syncWhatsAppTemplates,
  createWhatsAppTemplate,
  generateAITemplate,
  deleteWhatsAppTemplate,
  WhatsAppTemplateItem,
} from '@/services/whatsapp-templates-service';

export default function TemplatesPage() {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState<WhatsAppTemplateItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('all');

  // Modal Create / Edit State
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [editingTemplate, setEditingTemplate] = useState<WhatsAppTemplateItem | null>(null);
  const [isAIOpen, setIsAIOpen] = useState<boolean>(false);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Form State
  const [tplName, setTplName] = useState<string>('');
  const [tplCategory, setTplCategory] = useState<'MARKETING' | 'UTILITY' | 'AUTHENTICATION'>('MARKETING');
  const [tplLanguage, setTplLanguage] = useState<string>('es');
  const [headerText, setHeaderText] = useState<string>('');
  const [bodyText, setBodyText] = useState<string>('');
  const [footerText, setFooterText] = useState<string>('');
  const [buttonText, setButtonText] = useState<string>('');

  // AI Prompt State
  const [aiGoal, setAiGoal] = useState<string>('Ofrecer descuento de bienvenida y cerrar agendamiento');
  const [aiAudience, setAiAudience] = useState<string>('Leads interesados en consultoría');

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const data = await getWhatsAppTemplates();
      setTemplates(data);
    } catch (err: any) {
      toast.error('Error al cargar plantillas de WhatsApp');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      const updated = await syncWhatsAppTemplates();
      setTemplates(updated);
      toast.success('Plantillas sincronizadas con Meta Graph API');
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Falló la sincronización con Meta');
    } finally {
      setSyncing(false);
    }
  };

  const handleEditClick = (tpl: WhatsAppTemplateItem) => {
    setEditingTemplate(tpl);
    setTplName(tpl.name);
    setTplCategory(tpl.category);
    setTplLanguage(tpl.language || 'es');

    const comps = tpl.components || [];
    const header = comps.find((c: any) => c.type === 'HEADER');
    const body = comps.find((c: any) => c.type === 'BODY');
    const footer = comps.find((c: any) => c.type === 'FOOTER');
    const btnComp = comps.find((c: any) => c.type === 'BUTTONS');

    setHeaderText(header?.text || '');
    setBodyText(body?.text || '');
    setFooterText(footer?.text || '');
    setButtonText(btnComp?.buttons?.[0]?.text || '');

    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tplName || !bodyText) {
      toast.error('Nombre y cuerpo del mensaje son requeridos');
      return;
    }

    try {
      setIsCreating(true);
      const components: any[] = [];
      if (headerText) {
        components.push({ type: 'HEADER', format: 'TEXT', text: headerText });
      }
      components.push({ type: 'BODY', text: bodyText });
      if (footerText) {
        components.push({ type: 'FOOTER', text: footerText });
      }
      if (buttonText) {
        components.push({
          type: 'BUTTONS',
          buttons: [{ type: 'QUICK_REPLY', text: buttonText }],
        });
      }

      if (editingTemplate) {
        const { updateWhatsAppTemplate } = await import('@/services/whatsapp-templates-service');
        const res = await updateWhatsAppTemplate(editingTemplate.id, {
          category: tplCategory,
          components,
        });

        if (res.success) {
          toast.success('Plantilla actualizada y enviada a re-revisión en Meta');
          setIsCreateOpen(false);
          setEditingTemplate(null);
          resetForm();
          loadTemplates();
        }
      } else {
        const res = await createWhatsAppTemplate({
          name: tplName,
          category: tplCategory,
          language: tplLanguage,
          components,
        });

        if (res.success) {
          toast.success('Plantilla enviada a revisión en Meta');
          setIsCreateOpen(false);
          resetForm();
          loadTemplates();
        }
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Error al guardar plantilla en Meta');
    } finally {
      setIsCreating(false);
    }
  };

  const handleGenerateAI = async () => {
    try {
      setIsGenerating(true);
      const suggestion = await generateAITemplate(aiGoal, aiAudience);
      if (suggestion) {
        setTplName(suggestion.name || 'promo_ia_optimizada');
        setTplCategory(suggestion.category || 'MARKETING');
        setTplLanguage(suggestion.language || 'es');

        const comps = suggestion.components || [];
        const header = comps.find((c: any) => c.type === 'HEADER');
        const body = comps.find((c: any) => c.type === 'BODY');
        const footer = comps.find((c: any) => c.type === 'FOOTER');
        const btnComp = comps.find((c: any) => c.type === 'BUTTONS');

        setHeaderText(header?.text || '');
        setBodyText(body?.text || '');
        setFooterText(footer?.text || '');
        setButtonText(btnComp?.buttons?.[0]?.text || '');

        setIsAIOpen(false);
        setIsCreateOpen(true);
        toast.success(`Estructura sugerida con Score IA: ${suggestion.ai_score || 92}%`);
      }
    } catch (err: any) {
      toast.error('Error generando estructura con IA');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm(t('templates.deleteConfirm', { defaultValue: '¿Deseas eliminar esta plantilla de Meta y de tu repositorio?' }))) {
      return;
    }
    try {
      const ok = await deleteWhatsAppTemplate(id);
      if (ok) {
        toast.success('Plantilla eliminada correctamente');
        setTemplates((prev) => prev.filter((t) => t.id !== id));
      }
    } catch (err: any) {
      toast.error('Error eliminando la plantilla');
    }
  };

  const resetForm = () => {
    setEditingTemplate(null);
    setTplName('');
    setHeaderText('');
    setBodyText('');
    setFooterText('');
    setButtonText('');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return (
          <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> {t('templates.statusApproved', { defaultValue: 'Aprobada' })}
          </Badge>
        );
      case 'PENDING':
        return (
          <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 flex items-center gap-1">
            <Clock className="w-3 h-3 animate-pulse" /> {t('templates.statusPending', { defaultValue: 'En Revisión' })}
          </Badge>
        );
      case 'REJECTED':
        return (
          <Badge className="bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> {t('templates.statusRejected', { defaultValue: 'Rechazada' })}
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredTemplates = templates.filter((tpl) => {
    if (activeTab === 'all') return true;
    return tpl.category === activeTab.toUpperCase();
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
            <FileText className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t('templates.title', { defaultValue: 'Plantillas de WhatsApp (HSM)' })}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t('templates.desc', { defaultValue: 'Crea, gestiona e incrementa conversiones con plantillas oficiales de Meta Cloud API optimizadas por IA.' })}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing} className="h-9">
            <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
            {t('templates.syncBtn', { defaultValue: 'Sincronizar con Meta' })}
          </Button>

          <Button variant="secondary" size="sm" onClick={() => setIsAIOpen(true)} className="h-9 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
            <Sparkles className="h-4 w-4 mr-2 text-emerald-500" />
            {t('templates.aiGenerateBtn', { defaultValue: 'Generar con IA' })}
          </Button>

          <Button size="sm" onClick={() => { resetForm(); setIsCreateOpen(true); }} className="h-9 bg-emerald-600 hover:bg-emerald-700 text-white">
            <Plus className="h-4 w-4 mr-2" />
            {t('templates.newTemplateBtn', { defaultValue: 'Nueva Plantilla' })}
          </Button>
        </div>
      </div>

      {/* Category Tabs */}
      <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-4 max-w-md mb-6">
          <TabsTrigger value="all">Todas ({templates.length})</TabsTrigger>
          <TabsTrigger value="marketing">{t('templates.categoryMarketing', { defaultValue: 'Marketing' })}</TabsTrigger>
          <TabsTrigger value="utility">{t('templates.categoryUtility', { defaultValue: 'Utilidad' })}</TabsTrigger>
          <TabsTrigger value="authentication">{t('templates.categoryAuth', { defaultValue: 'Autenticación' })}</TabsTrigger>
        </TabsList>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
          </div>
        ) : filteredTemplates.length === 0 ? (
          <Card className="p-12 text-center border-dashed">
            <MessageSquare className="h-10 w-10 mx-auto text-muted-foreground mb-3 opacity-50" />
            <h3 className="text-base font-semibold">No se encontraron plantillas</h3>
            <p className="text-xs text-muted-foreground mt-1 mb-4">
              Sincroniza tus plantillas existentes de Meta o crea una nueva optimizada con IA.
            </p>
            <Button size="sm" onClick={() => setIsAIOpen(true)} className="bg-emerald-600 text-white">
              <Sparkles className="h-4 w-4 mr-2" /> Generar Primera Plantilla con IA
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredTemplates.map((tpl) => {
              const comps = tpl.components || [];
              const header = comps.find((c: any) => c.type === 'HEADER');
              const body = comps.find((c: any) => c.type === 'BODY');
              const footer = comps.find((c: any) => c.type === 'FOOTER');
              const buttons = comps.find((c: any) => c.type === 'BUTTONS')?.buttons || [];

              return (
                <Card key={tpl.id} className="flex flex-col justify-between hover:shadow-md transition-all border-border/80">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wider">
                        {tpl.category}
                      </Badge>
                      {getStatusBadge(tpl.status)}
                    </div>
                    <CardTitle className="text-base mt-2 font-mono break-all">{tpl.name}</CardTitle>
                    <CardDescription className="text-xs flex items-center gap-3 mt-1">
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                        <TrendingUp className="w-3.5 h-3.5" />
                        {tpl.conversion_rate || 0}% Conv.
                      </span>
                      <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400 font-medium">
                        <Sparkles className="w-3.5 h-3.5" />
                        Score: {tpl.ai_performance_score || 85}/100
                      </span>
                    </CardDescription>
                  </CardHeader>

                  {/* Simulated WhatsApp Bubble */}
                  <CardContent className="py-2">
                    <div className="bg-emerald-500/5 dark:bg-emerald-950/20 border border-emerald-500/10 p-3.5 rounded-2xl space-y-2 text-xs">
                      {header && <p className="font-bold text-foreground">{header.text}</p>}
                      {body && <p className="text-muted-foreground whitespace-pre-line leading-relaxed">{body.text}</p>}
                      {footer && <p className="text-[10px] text-muted-foreground/70 border-t pt-1.5 mt-2">{footer.text}</p>}
                      {buttons.length > 0 && (
                        <div className="pt-2 border-t space-y-1.5">
                          {buttons.map((btn: any, idx: number) => (
                            <div key={idx} className="bg-background text-emerald-600 dark:text-emerald-400 font-medium py-1.5 px-3 rounded-lg text-center border text-[11px] flex items-center justify-center gap-1.5 shadow-2xs">
                              <Send className="w-3 h-3" /> {btn.text}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </CardContent>

                  <div className="p-4 pt-2 flex items-center justify-between border-t mt-3 text-xs text-muted-foreground">
                    <span className="font-mono">ID: {tpl.meta_template_id || 'Local'}</span>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={() => handleEditClick(tpl)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10" onClick={() => handleDelete(tpl.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </Tabs>

      {/* Modal: Create Template */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {editingTemplate ? <Pencil className="h-5 w-5 text-emerald-600" /> : <Plus className="h-5 w-5 text-emerald-600" />}
              {editingTemplate ? `Editar Plantilla: ${editingTemplate.name}` : 'Nueva Plantilla de WhatsApp (Meta Cloud API)'}
            </DialogTitle>
            <DialogDescription className="text-xs">
              {editingTemplate
                ? 'Modifica el contenido o categoría de tu plantilla. Al guardar, Meta volverá a evaluarla para aprobación.'
                : 'Estructura el contenido de tu plantilla HSM. Se enviará a revisión en Meta Developers automáticamente.'}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateSubmit} className="space-y-4 py-2">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="tpl-name" className="text-xs">Nombre de Plantilla (minúsculas y guiones bajos)</Label>
                <Input id="tpl-name" placeholder="oferta_bienvenida_v1" disabled={!!editingTemplate} value={tplName} onChange={(e) => setTplName(e.target.value.toLowerCase().replace(/ /g, '_'))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tpl-cat" className="text-xs">Categoría Meta</Label>
                <select id="tpl-cat" className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs" value={tplCategory} onChange={(e: any) => setTplCategory(e.target.value)}>
                  <option value="MARKETING">Marketing (Promocional / Ventas)</option>
                  <option value="UTILITY">Utilidad (Notificaciones / Updates)</option>
                  <option value="AUTHENTICATION">Autenticación (OTP / PIN)</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tpl-lang" className="text-xs">Idioma Meta</Label>
                <select
                  id="tpl-lang"
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs disabled:opacity-60 disabled:cursor-not-allowed"
                  disabled={!!editingTemplate}
                  value={tplLanguage}
                  onChange={(e) => setTplLanguage(e.target.value)}
                >
                  <option value="es">Español (es)</option>
                  <option value="es_LA">Español - Latinoamérica (es_LA)</option>
                  <option value="es_ES">Español - España (es_ES)</option>
                  <option value="en">Inglés - General (en)</option>
                  <option value="en_US">Inglés - EE. UU. (en_US)</option>
                  <option value="en_GB">Inglés - Reino Unido (en_GB)</option>
                  <option value="pt_BR">Portugués - Brasil (pt_BR)</option>
                  <option value="pt_PT">Portugués - Portugal (pt_PT)</option>
                  <option value="fr">Francés (fr)</option>
                  <option value="de">Alemán (de)</option>
                  <option value="it">Italiano (it)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tpl-header" className="text-xs">Header / Encabezado (Opcional)</Label>
              <Input id="tpl-header" placeholder="🚀 ¡Oferta Exclusiva para ti!" value={headerText} onChange={(e) => setHeaderText(e.target.value)} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tpl-body" className="text-xs">Body / Cuerpo del Mensaje (Usa &#123;&#123;1&#125;&#125;, &#123;&#123;2&#125;&#125; para variables)</Label>
              <textarea id="tpl-body" rows={4} className="w-full rounded-md border border-input bg-background p-3 text-xs leading-relaxed" placeholder="Hola {{1}}, tenemos una propuesta especial de {{2}}..." value={bodyText} onChange={(e) => setBodyText(e.target.value)} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="tpl-footer" className="text-xs">Footer / Pie de página (Opcional)</Label>
                <Input id="tpl-footer" placeholder="Responde para cancelar suscripción" value={footerText} onChange={(e) => setFooterText(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tpl-btn" className="text-xs">Botón de Respuesta Rápida (Opcional)</Label>
                <Input id="tpl-btn" placeholder="Quiero saber más" value={buttonText} onChange={(e) => setButtonText(e.target.value)} />
              </div>
            </div>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={isCreating} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {isCreating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                Enviar a Revisión en Meta
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal: AI Optimizer Generator */}
      <Dialog open={isAIOpen} onOpenChange={setIsAIOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-emerald-600">
              <Sparkles className="h-5 w-5" />
              Optimizador de Conversión con IA
            </DialogTitle>
            <DialogDescription className="text-xs">
              La IA analizará el objetivo de tu campaña y estructurará una plantilla HSM optimizada para mayor porcentaje de respuesta.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="ai-goal" className="text-xs">Objetivo de la Plantilla</Label>
              <Input id="ai-goal" value={aiGoal} onChange={(e) => setAiGoal(e.target.value)} placeholder="Ej. Recuperar carritos abandonados" />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ai-aud" className="text-xs">Público / Segmento de Leads</Label>
              <Input id="ai-aud" value={aiAudience} onChange={(e) => setAiAudience(e.target.value)} placeholder="Ej. Clientes que preguntaron por precios" />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsAIOpen(false)}>Cancelar</Button>
              <Button onClick={handleGenerateAI} disabled={isGenerating} className="bg-emerald-600 text-white">
                {isGenerating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                Generar Estructura con IA
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
