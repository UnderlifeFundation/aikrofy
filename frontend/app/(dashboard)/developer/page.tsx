'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  Key,
  Coins,
  Copy,
  Check,
  RefreshCw,
  Code,
  BookOpen,
  Activity,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Server,
  Zap,
  ChevronRight
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api-client';
import { useAuthStore } from '@/store/use-auth-store';
import { useTranslation } from 'react-i18next';

export default function DeveloperAPIPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const companyId = user?.company_id;

  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'rest' | 'mcp'>('rest');
  const [selectedOp, setSelectedOp] = useState<string>('invoke_agent');

  // Fetch company data to get plan_type and credit_balance
  const { data: companyData, isLoading: isLoadingCompany } = useQuery({
    queryKey: ['developer-company-data', companyId],
    queryFn: async () => {
      if (!companyId) return null;
      const { data } = await apiClient.get(`/auth/me`);
      return data.data.company;
    },
    enabled: !!companyId,
  });

  // Generate API key mutation
  const generateKeyMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post(`/companies/${companyId}/api-key/generate`);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['developer-company-data', companyId] });
      toast.success(t('developer.toastApiKeyGenerated', 'Nueva API Key pública generada.'));
      // Copy to clipboard immediately
      if (data.api_key) {
        navigator.clipboard.writeText(data.api_key);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        toast.info(t('developer.toastApiKeyCopied', 'API Key copiada al portapapeles.'));
      }
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || t('developer.toastErrorGenerate', 'Error al generar API Key'));
    }
  });

  // Purchase credits / tokens simulation
  const buyCreditsMutation = useMutation({
    mutationFn: async (amount: number) => {
      // Simulates paddle/paypal checkout or direct increment for demo/use case
      // In production, redirects to payment gateway
      toast.info(t('developer.toastRedirectingPayment', 'Redirigiendo a pasarela de pagos...'));
      return new Promise((resolve) => setTimeout(resolve, 1000));
    },
    onSuccess: () => {
      toast.success(t('developer.toastCreditsUpdated', 'Compra completada con éxito. Créditos actualizados.'));
    }
  });

  const handleCopy = (keyText: string) => {
    if (!keyText) return;
    navigator.clipboard.writeText(keyText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success(t('developer.toastKeyCopied', 'API Key copiada.'));
  };

  const getApiKeyDisplay = () => {
    const key = companyData?.api_keys?.public_api_key;
    if (!key) return t('developer.noKeyGenerated', 'No se ha generado ninguna API Key aún.');
    return key;
  };

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="relative rounded-3xl bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 p-8 text-white overflow-hidden shadow-xl">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <Cpu className="h-40 w-40" />
        </div>
        <div className="relative z-10 space-y-4 max-w-3xl">
          <Badge className="bg-white/20 hover:bg-white/30 text-white border-none py-1 px-3">
            <Sparkles className="h-3 w-3 mr-1 text-amber-300" />
            Developer Platform v1
          </Badge>
          <h1 className="text-4xl font-extrabold tracking-tight">{t('developer.title', 'Ecosistema API & MCP como Servicio')}</h1>
          <p className="text-white/80 text-base max-w-2xl leading-relaxed">
            {t('developer.description', 'Consumir la inteligencia de la junta directiva y herramientas atómicas (RAG, cobros, CRM) directamente en tus propias aplicaciones, plugins o clientes de IA externos (como Claude Desktop).')}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* API Credentials & Tokens panel */}
        <div className="space-y-6 lg:col-span-1">
          {/* Key Manager */}
          <Card className="shadow-lg border-border">
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Key className="h-5 w-5 text-indigo-500" />
                {t('developer.credentialsTitle', 'API Credentials')}
              </CardTitle>
              <CardDescription>{t('developer.credentialsDesc', 'Usa esta clave para autenticar llamadas REST o conexiones MCP.')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-muted rounded-xl border border-border flex items-center justify-between gap-3 overflow-hidden">
                <code className="text-xs font-mono truncate text-foreground select-all">
                  {getApiKeyDisplay()}
                </code>
                {companyData?.api_keys?.public_api_key && (
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 shrink-0 hover:bg-background"
                    onClick={() => handleCopy(companyData.api_keys.public_api_key)}
                  >
                    {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                  </Button>
                )}
              </div>
              <Button
                variant="outline"
                className="w-full flex items-center justify-center gap-2"
                onClick={() => generateKeyMutation.mutate()}
                disabled={generateKeyMutation.isPending}
              >
                {generateKeyMutation.isPending ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                {t('developer.generateNewKey', 'Generar nueva clave')}
              </Button>
            </CardContent>
            <CardFooter className="bg-muted/50 text-[10px] text-muted-foreground p-3 border-t">
              {t('developer.keyWarning', 'Nota: Generar una nueva clave revocará inmediatamente la anterior. Guarde la clave de forma segura.')}
            </CardFooter>
          </Card>

          {/* Token Dashboard */}
          <Card className="shadow-lg border-border relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <Coins className="h-24 w-24 text-amber-500" />
            </div>
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Coins className="h-5 w-5 text-amber-500" />
                {t('developer.tokenBalance', 'Balance de Tokens')}
              </CardTitle>
              <CardDescription>{t('developer.tokensDesc', 'Cada llamada de agente o acción consume créditos según el uso.')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <div className="py-6">
                <span className="text-5xl font-black text-foreground">
                  {companyData?.credit_balance ?? 0}
                </span>
                <span className="text-amber-500 text-lg font-bold ml-1">🪙</span>
                <p className="text-xs text-muted-foreground mt-2">{t('developer.tokensAvailable', 'Tokens disponibles en tu plan')}</p>
              </div>
              <Separator />
              <div className="grid grid-cols-3 gap-2 pt-2">
                {[
                  { tokens: 100, price: '$5' },
                  { tokens: 500, price: '$20' },
                  { tokens: 2000, price: '$70' }
                ].map((pack) => (
                  <Button
                    key={pack.tokens}
                    variant="outline"
                    className="flex flex-col gap-1 py-3 h-auto"
                    onClick={() => buyCreditsMutation.mutate(pack.tokens)}
                  >
                    <span className="text-xs font-bold font-mono">+{pack.tokens} 🪙</span>
                    <span className="text-[10px] text-muted-foreground font-semibold">{pack.price}</span>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* REST API & MCP Catalog */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="shadow-lg border-border">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg font-bold flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-primary" />
                    {t('developer.catalogTitle', 'Catálogo de Servicios')}
                  </CardTitle>
                  <CardDescription>{t('developer.catalogDesc', 'Explora y testea la documentación de macro y micro operaciones.')}</CardDescription>
                </div>
                <div className="flex border rounded-xl overflow-hidden p-0.5 bg-muted">
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn("px-4 py-1.5 h-auto text-xs rounded-lg font-semibold", activeTab === 'rest' && "bg-background shadow")}
                    onClick={() => setActiveTab('rest')}
                  >
                    REST API
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn("px-4 py-1.5 h-auto text-xs rounded-lg font-semibold", activeTab === 'mcp' && "bg-background shadow")}
                    onClick={() => setActiveTab('mcp')}
                  >
                    MCP Server
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {activeTab === 'rest' ? (
                <div className="grid grid-cols-1 md:grid-cols-3 min-h-[450px]">
                  {/* Operations List */}
                  <div className="border-r border-border md:col-span-1 p-4 space-y-2">
                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-2">{t('developer.macroOps', 'Macro Operaciones')}</p>
                    <button
                      onClick={() => setSelectedOp('invoke_agent')}
                      className={cn(
                        "w-full text-left p-3 rounded-xl transition-all text-xs font-semibold flex items-center justify-between",
                        selectedOp === 'invoke_agent' ? "bg-primary/10 text-primary" : "hover:bg-muted"
                      )}
                    >
                      <span>{t('developer.invokeCSuite', 'Invocar Agente C-Suite')}</span>
                      <ChevronRight className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => setSelectedOp('query_knowledge')}
                      className={cn(
                        "w-full text-left p-3 rounded-xl transition-all text-xs font-semibold flex items-center justify-between",
                        selectedOp === 'query_knowledge' ? "bg-primary/10 text-primary" : "hover:bg-muted"
                      )}
                    >
                      <span>{t('developer.ragQuery', 'Consulta RAG Compartida')}</span>
                      <ChevronRight className="h-3 w-3" />
                    </button>

                    <Separator className="my-4" />
                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-2">{t('developer.microOps', 'Micro Operaciones')}</p>
                    <button
                      onClick={() => setSelectedOp('ingest_doc')}
                      className={cn(
                        "w-full text-left p-3 rounded-xl transition-all text-xs font-semibold flex items-center justify-between",
                        selectedOp === 'ingest_doc' ? "bg-primary/10 text-primary" : "hover:bg-muted"
                      )}
                    >
                      <span>{t('developer.ingestRag', 'Ingestar Documento RAG')}</span>
                      <ChevronRight className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Operation Detail */}
                  <div className="md:col-span-2 p-6 space-y-6">
                    {selectedOp === 'invoke_agent' && (
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/10 border-none font-bold">POST</Badge>
                          <code className="text-xs font-mono font-bold text-foreground">/v1/agents/invoke</code>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {t('developer.opInvokeDesc', 'Invoca un agente específico de la Junta Directiva (CEO, CMO, CFO, CRO, COO, CTO, CSO) pasándole el prompt. Las respuestas son automáticas y toman en cuenta la base de conocimientos global de BOS-AI.')}
                        </p>
                        <div className="space-y-2">
                          <p className="text-xs font-bold">{t('developer.requiredHeaders', 'Headers Requeridos:')}</p>
                          <pre className="p-3 bg-muted rounded-xl border border-border text-[11px] font-mono text-muted-foreground">
{`X-API-Key: aikrofy_your_public_api_key
Content-Type: application/json`}
                          </pre>
                        </div>
                        <div className="space-y-2">
                          <p className="text-xs font-bold">{t('developer.inputPayload', 'Payload de Entrada:')}</p>
                          <pre className="p-3 bg-muted rounded-xl border border-border text-[11px] font-mono text-muted-foreground">
{`{
  "agent_role": "cfo",
  "prompt": "${t('developer.promptPlaceholder', 'Analiza las metas financieras de este Q3 basándote en los manuales de BOS-AI')}"
}`}
                          </pre>
                        </div>
                      </div>
                    )}

                    {selectedOp === 'query_knowledge' && (
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/10 border-none font-bold">POST</Badge>
                          <code className="text-xs font-mono font-bold text-foreground">/v1/knowledge/query</code>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {t('developer.opQueryDesc', 'Realiza una búsqueda semántica de vectores tanto en la base de conocimientos privada de la empresa como en la base global compartida del sistema.')}
                        </p>
                        <div className="space-y-2">
                          <p className="text-xs font-bold">{t('developer.inputPayload', 'Payload de Entrada:')}</p>
                          <pre className="p-3 bg-muted rounded-xl border border-border text-[11px] font-mono text-muted-foreground">
{`{
  "query": "${t('developer.queryPlaceholder', 'Manejo de objeciones de precios en ventas')}",
  "top_k": 3,
  "include_global": true
}`}
                          </pre>
                        </div>
                      </div>
                    )}

                    {selectedOp === 'ingest_doc' && (
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/10 border-none font-bold">POST</Badge>
                          <code className="text-xs font-mono font-bold text-foreground">/v1/knowledge/ingest</code>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {t('developer.opIngestDesc', 'Sube un archivo de texto o PDF plano directamente a la base de conocimiento vectorial (RAG) privada de tu empresa para que tus agentes puedan empezar a utilizarlo al instante.')}
                        </p>
                        <div className="space-y-2">
                          <p className="text-xs font-bold">Multipart Form-data:</p>
                          <pre className="p-3 bg-muted rounded-xl border border-border text-[11px] font-mono text-muted-foreground">
{`file: [Archivo binario en formato de texto plano / PDF]`}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-6 space-y-6 min-h-[450px]">
                  <div className="flex items-start gap-4 p-4 bg-primary/5 border border-primary/10 rounded-2xl">
                    <Server className="h-6 w-6 text-primary shrink-0 mt-0.5" />
                    <div>
                      <h3 className="text-sm font-bold">Model Context Protocol (MCP) Server</h3>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        {t('developer.mcpDescription', 'Conecta tus agentes del sistema a Claude Desktop o asistentes de desarrollo. Al configurar nuestro servidor de MCP, tus IAs podrán consultar la base de conocimiento o invocar comandos del dashboard de manera nativa.')}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t('developer.connectionInstructions', 'Instrucciones de Conexión')}</h3>
                    <div className="p-4 bg-muted border border-border rounded-xl font-mono text-xs text-muted-foreground space-y-3">
                      <p className="font-semibold text-foreground">{t('developer.mcpConfigJson', 'En tu archivo claude_desktop_config.json:')}</p>
                      <pre className="overflow-auto max-h-[300px]">
{`{
  "mcpServers": {
    "executiv-csuite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-http",
        "--url",
        "https://api.aikrofy.com/api/mcp"
      ],
      "env": {
        "X_API_KEY": "${companyData?.api_keys?.public_api_key || 'aikrofy_your_public_api_key'}"
      }
    }
  }
}`}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
