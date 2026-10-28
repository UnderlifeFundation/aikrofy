'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Wrench, 
  Plus, 
  Trash2, 
  Globe, 
  Key, 
  CheckCircle2, 
  AlertCircle, 
  Code, 
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Server
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

export interface DynamicActionItem {
  id: number;
  name: string;
  display_name: string;
  description: string;
  endpoint_url: string;
  http_method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  auth_type: 'none' | 'bearer' | 'api_key' | 'basic';
  parameters_schema?: any[];
  headers?: Record<string, string>;
  is_active: boolean;
}

export function ActionConnectorsManager() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  
  // Form State
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [endpointUrl, setEndpointUrl] = useState('');
  const [httpMethod, setHttpMethod] = useState<'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'>('POST');
  const [authType, setAuthType] = useState<'none' | 'bearer' | 'api_key' | 'basic'>('none');
  const [authSecret, setAuthSecret] = useState('');
  const [apiKeyHeader, setApiKeyHeader] = useState('X-API-Key');
  const [parametersSchemaJson, setParametersSchemaJson] = useState('[\n  {\n    "name": "query",\n    "type": "string",\n    "description": "Término de búsqueda",\n    "required": true\n  }\n]');

  const { data: actions = [], isLoading } = useQuery<DynamicActionItem[]>({
    queryKey: ['enterprise-actions'],
    queryFn: async () => {
      const res = await apiClient.get('/enterprise/actions');
      return res.data?.actions || [];
    }
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      let parsedSchema = [];
      try {
        parsedSchema = JSON.parse(parametersSchemaJson);
      } catch (e) {
        throw new Error('El esquema de parámetros JSON no es válido.');
      }

      let authConfig: any = {};
      if (authType === 'bearer') {
        authConfig = { token: authSecret };
      } else if (authType === 'api_key') {
        authConfig = { key_name: apiKeyHeader, key_value: authSecret, in: 'header' };
      }

      const payload = {
        name,
        display_name: displayName || name,
        description,
        endpoint_url: endpointUrl,
        http_method: httpMethod,
        auth_type: authType,
        auth_config: authConfig,
        parameters_schema: parsedSchema
      };

      const res = await apiClient.post('/enterprise/actions', payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Conector de Acción creado y expuesto al agente LangGraph');
      queryClient.invalidateQueries({ queryKey: ['enterprise-actions'] });
      setIsCreateOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.error('Error al crear conector: ' + (err.response?.data?.error || err.message));
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/enterprise/actions/${id}`);
    },
    onSuccess: () => {
      toast.success('Conector eliminado');
      queryClient.invalidateQueries({ queryKey: ['enterprise-actions'] });
    },
    onError: (err: any) => {
      toast.error('Error al eliminar conector: ' + (err.response?.data?.error || err.message));
    }
  });

  const resetForm = () => {
    setName('');
    setDisplayName('');
    setDescription('');
    setEndpointUrl('');
    setHttpMethod('POST');
    setAuthType('none');
    setAuthSecret('');
    setParametersSchemaJson('[\n  {\n    "name": "query",\n    "type": "string",\n    "description": "Término de búsqueda",\n    "required": true\n  }\n]');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card border rounded-2xl p-5 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 shadow-xs">
              <Wrench className="h-4 w-4" />
            </div>
            <h3 className="text-lg font-bold">Conectores de Acción No-Code (API Tools)</h3>
            <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-600 border-emerald-200">
              LangGraph Dynamic Tools
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Conecta tus agentes a cualquier API REST o webhook en segundos sin programar código. Los agentes razonarán automáticamente cuándo invocar estas herramientas.
          </p>
        </div>

        <Button
          onClick={() => setIsCreateOpen(true)}
          size="sm"
          className="text-xs gap-1.5 vivid-gradient-violet text-white shadow-md hover:opacity-95 self-start sm:self-center"
        >
          <Plus className="w-3.5 h-3.5" />
          Nuevo Conector
        </Button>
      </div>

      {/* Grid of Connectors */}
      {isLoading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">
          Cargando conectores...
        </div>
      ) : actions.length === 0 ? (
        <Card className="p-12 text-center border-dashed">
          <div className="flex flex-col items-center gap-3 text-muted-foreground">
            <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-full">
              <Server className="w-6 h-6 text-slate-500" />
            </div>
            <h4 className="font-semibold text-sm text-foreground">No tienes conectores REST registrados</h4>
            <p className="text-xs max-w-sm">
              Crea tu primer conector para permitir que tus agentes consulten stocks, verifiquen estados de pedidos o ejecuten mutaciones externas.
            </p>
            <Button size="sm" onClick={() => setIsCreateOpen(true)} variant="outline" className="mt-2 text-xs">
              Crear mi primer conector
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {actions.map((act) => (
            <Card key={act.id} className="border-border hover:shadow-md transition-shadow">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono text-[10px] px-1.5 uppercase font-bold text-violet-600 bg-violet-50 dark:bg-violet-950/30">
                      {act.http_method}
                    </Badge>
                    <span className="font-semibold text-sm line-clamp-1">{act.display_name}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteMutation.mutate(act.id)}
                    disabled={deleteMutation.isPending}
                    className="h-7 w-7 text-muted-foreground hover:text-rose-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
                <CardDescription className="text-xs mt-1 font-mono text-muted-foreground line-clamp-1">
                  {act.endpoint_url}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 pt-2">
                <p className="text-xs text-foreground/80 line-clamp-2 mb-3">
                  {act.description || 'Sin descripción provista.'}
                </p>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t pt-2.5">
                  <span className="flex items-center gap-1">
                    <Key className="w-3 h-3 text-amber-500" />
                    Auth: <span className="font-semibold uppercase">{act.auth_type}</span>
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-200">
                    Activo en LangGraph
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Connector Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Wrench className="w-4 h-4 text-violet-500" />
              Nuevo Conector de Acción REST
            </DialogTitle>
            <DialogDescription className="text-xs">
              Define los parámetros y el endpoint que el modelo invocará de forma autónoma.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Identificador Técnico (Tool Name)</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                  placeholder="ej. consultar_saldo"
                  className="text-xs font-mono"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Nombre Descriptivo</Label>
                <Input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Consultar Saldo Cliente"
                  className="text-xs"
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">Descripción para el Agente (Decisión semántica)</Label>
              <Textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Usa esta herramienta cuando el cliente pida conocer su saldo actual o facturas pendientes..."
                className="text-xs"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-1 space-y-1">
                <Label className="text-xs">Método HTTP</Label>
                <Select value={httpMethod} onValueChange={(val: any) => setHttpMethod(val)}>
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="DELETE">DELETE</SelectItem>
                    <SelectItem value="PATCH">PATCH</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-2 space-y-1">
                <Label className="text-xs">URL del Endpoint</Label>
                <Input
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  placeholder="https://api.empresa.com/v1/customers/balance"
                  className="text-xs font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Tipo de Autenticación</Label>
                <Select value={authType} onValueChange={(val: any) => setAuthType(val)}>
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin autenticación</SelectItem>
                    <SelectItem value="bearer">Bearer Token</SelectItem>
                    <SelectItem value="api_key">API Key Header</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {authType !== 'none' && (
                <div className="space-y-1">
                  <Label className="text-xs">Token o Clave Secreta</Label>
                  <Input
                    type="password"
                    value={authSecret}
                    onChange={(e) => setAuthSecret(e.target.value)}
                    placeholder="eyJhbGciOi..."
                    className="text-xs font-mono"
                  />
                </div>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Parámetros del Tool (Esquema JSON)</Label>
                <span className="text-[10px] text-muted-foreground font-mono">Pydantic / OpenAI Schema</span>
              </div>
              <Textarea
                rows={5}
                value={parametersSchemaJson}
                onChange={(e) => setParametersSchemaJson(e.target.value)}
                className="text-xs font-mono bg-slate-950 text-slate-100"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="ghost" size="sm" onClick={() => setIsCreateOpen(false)} className="text-xs">
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !name || !endpointUrl}
              className="text-xs vivid-gradient-violet text-white"
            >
              {createMutation.isPending ? <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
              Crear Conector
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
