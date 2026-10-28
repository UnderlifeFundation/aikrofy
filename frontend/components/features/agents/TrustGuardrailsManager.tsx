'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  ShieldAlert, 
  ShieldCheck, 
  Lock, 
  EyeOff, 
  Percent, 
  AlertTriangle, 
  CheckCircle2, 
  Plus, 
  Trash2,
  RefreshCw,
  Scale
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

export interface GuardrailItem {
  id: number;
  name: string;
  guardrail_type: 'pii_masking' | 'max_discount' | 'sentiment_escalation' | 'topic_ban' | 'tool_authorization';
  config: Record<string, any>;
  action_on_violation: 'block' | 'mask' | 'escalate' | 'warn';
  is_active: boolean;
}

export function TrustGuardrailsManager() {
  const queryClient = useQueryClient();
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Form State
  const [name, setName] = useState('');
  const [type, setType] = useState<'pii_masking' | 'max_discount' | 'sentiment_escalation' | 'topic_ban' | 'tool_authorization'>('max_discount');
  const [actionViolation, setActionViolation] = useState<'block' | 'mask' | 'escalate' | 'warn'>('block');
  const [maxDiscountVal, setMaxDiscountVal] = useState('15');
  const [blockedTopics, setBlockedTopics] = useState('competencia, política, contraseñas');

  const { data: guardrails = [], isLoading } = useQuery<GuardrailItem[]>({
    queryKey: ['enterprise-guardrails'],
    queryFn: async () => {
      const res = await apiClient.get('/enterprise/guardrails');
      return res.data?.guardrails || [];
    }
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      let config: any = {};
      if (type === 'max_discount') {
        config = { max_percentage: parseFloat(maxDiscountVal) || 15 };
      } else if (type === 'topic_ban') {
        config = { banned_topics: blockedTopics.split(',').map(s => s.trim()).filter(Boolean) };
      } else if (type === 'pii_masking') {
        config = { mask_credit_cards: true, mask_ssn: true, mask_emails: false };
      }

      const payload = {
        name: name || `Regla de ${type}`,
        guardrail_type: type,
        action_on_violation: actionViolation,
        config
      };

      const res = await apiClient.post('/enterprise/guardrails', payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Guardrail de confianza activado en LangGraph');
      queryClient.invalidateQueries({ queryKey: ['enterprise-guardrails'] });
      setIsAddOpen(false);
      setName('');
    },
    onError: (err: any) => {
      toast.error('Error al registrar guardrail: ' + (err.response?.data?.error || err.message));
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/enterprise/guardrails/${id}`);
    },
    onSuccess: () => {
      toast.success('Guardrail eliminado');
      queryClient.invalidateQueries({ queryKey: ['enterprise-guardrails'] });
    },
    onError: (err: any) => {
      toast.error('Error al eliminar guardrail: ' + (err.response?.data?.error || err.message));
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card border rounded-2xl p-5 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 shadow-xs">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <h3 className="text-lg font-bold">Trust & Governance Guardrails (Capa de Seguridad)</h3>
            <Badge variant="outline" className="text-xs bg-indigo-500/10 text-indigo-600 border-indigo-200">
              Zero Hallucination & Risk Prevention
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Protección de datos (PII Masking), límites estrictos de descuentos comerciales y blindaje contra alucinaciones críticas al estilo Salesforce Einstein Trust Layer.
          </p>
        </div>

        <Button
          onClick={() => setIsAddOpen(true)}
          size="sm"
          className="text-xs gap-1.5 vivid-gradient-violet text-white shadow-md hover:opacity-95 self-start sm:self-center"
        >
          <Plus className="w-3.5 h-3.5" />
          Nueva Regla de Seguridad
        </Button>
      </div>

      {/* Preset Default Cards: PII & Operational Governance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-border">
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <EyeOff className="w-4 h-4 text-emerald-500" />
                <CardTitle className="text-sm font-semibold">Enmascaramiento PII Automático</CardTitle>
              </div>
              <Badge className="bg-emerald-500 text-white text-[10px]">Activo por Defecto</Badge>
            </div>
            <CardDescription className="text-xs mt-1">
              Ofusca números de tarjetas de crédito (`**** **** **** 1234`) y cédulas o identificaciones personales antes de que el texto llegue a proveedores LLM.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground border-t pt-2.5">
              <span>Auditoría de Cumplimiento</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">GDPR & PCI-DSS Compliant</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-amber-500" />
                <CardTitle className="text-sm font-semibold">Límites Comerciales Autónomos</CardTitle>
              </div>
              <Badge variant="outline" className="text-amber-600 border-amber-300 text-[10px]">Protección Activa</Badge>
            </div>
            <CardDescription className="text-xs mt-1">
              Impide que los agentes ofrezcan promociones, gratuidades o rebajas mayores al tope de la empresa sin autorización explícita de un supervisor.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground border-t pt-2.5">
              <span>Máximo Descuento Permitido</span>
              <span className="font-semibold text-amber-600 dark:text-amber-400">Hasta 20% (Regla Corporativa)</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dynamic Guardrails List */}
      {isLoading ? (
        <div className="text-center py-8 text-xs text-muted-foreground">Cargando políticas...</div>
      ) : guardrails.length === 0 ? null : (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Políticas Personalizadas de la Empresa</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {guardrails.map((g) => (
              <Card key={g.id} className="border-border p-4 shadow-xs">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="font-semibold text-sm">{g.name}</span>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">
                      Tipo: {g.guardrail_type} | Acción: {g.action_on_violation}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteMutation.mutate(g.id)}
                    className="h-7 w-7 text-muted-foreground hover:text-rose-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Add Guardrail Modal */}
      <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <ShieldAlert className="w-4 h-4 text-violet-500" />
              Nueva Política de Guardrail
            </DialogTitle>
            <DialogDescription className="text-xs">
              Asegura que las respuestas y acciones del modelo se mantengan en los límites corporativos permitidos.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <Label className="text-xs">Nombre de la Regla</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="ej. Bloqueo de Descuentos Mayores al 15%"
                className="text-xs"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs">Tipo de Guardrail</Label>
              <Select value={type} onValueChange={(val: any) => setType(val)}>
                <SelectTrigger className="text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="max_discount">Límite de Descuento Comercial</SelectItem>
                  <SelectItem value="topic_ban">Prohibición de Temas Sensibles</SelectItem>
                  <SelectItem value="pii_masking">Enmascaramiento de Datos Privados (PII)</SelectItem>
                  <SelectItem value="sentiment_escalation">Escalamiento por Frustración / Enojo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {type === 'max_discount' && (
              <div className="space-y-1">
                <Label className="text-xs">Porcentaje Máximo Permitido (%)</Label>
                <Input
                  type="number"
                  value={maxDiscountVal}
                  onChange={(e) => setMaxDiscountVal(e.target.value)}
                  className="text-xs font-mono"
                  placeholder="15"
                />
              </div>
            )}

            {type === 'topic_ban' && (
              <div className="space-y-1">
                <Label className="text-xs">Palabras Clave / Temas Prohibidos (separados por coma)</Label>
                <Input
                  value={blockedTopics}
                  onChange={(e) => setBlockedTopics(e.target.value)}
                  className="text-xs"
                  placeholder="competidor_x, finanzas_privadas, quejas"
                />
              </div>
            )}

            <div className="space-y-1">
              <Label className="text-xs">Acción en caso de Violación</Label>
              <Select value={actionViolation} onValueChange={(val: any) => setActionViolation(val)}>
                <SelectTrigger className="text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="block">Bloquear Ejecución y Advertir al Agente</SelectItem>
                  <SelectItem value="escalate">Traspasar Inmediatamente a Supervisor Humano</SelectItem>
                  <SelectItem value="mask">Enmascarar Contenido Ofensivo / Privado</SelectItem>
                  <SelectItem value="warn">Permitir y Notificar en Logs de Auditoría</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsAddOpen(false)} className="text-xs">
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="text-xs vivid-gradient-violet text-white"
            >
              {createMutation.isPending ? <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
              Activar Regla
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
