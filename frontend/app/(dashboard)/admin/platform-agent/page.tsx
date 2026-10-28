'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Cookies from 'js-cookie';
import { useRouter } from 'next/navigation';
import { Bot, Save, Loader2, MessageSquare, Zap, Shield, Globe, FileText } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

export default function PlatformAgentPage() {
    const { t } = useTranslation();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/admin/platform-agent');
            setData(response.data.data);
        } catch (error) {
            console.error('Error fetching platform agent:', error);
            toast.error(t('platformAgent.loadError', 'Error al cargar la configuración del agente'));
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            
            const payload = data ? {
                company: {
                    name: data.company.name,
                },
                agent: {
                    name: data.agent.name,
                    tone: data.agent.tone,
                    objective: data.agent.objective,
                    system_prompt: data.agent.system_prompt,
                    features: data.agent.features
                }
            } : {};

            await apiClient.post('/admin/platform-agent', payload);
            toast.success(t('platformAgent.saveSuccess', 'Configuración guardada correctamente'));
            
            fetchData();
        } catch (error) {
            console.error('Error saving platform agent:', error);
            toast.error(t('platformAgent.saveError', 'Error al guardar la configuración'));
        } finally {
            setSaving(false);
        }
    };

    const toggleFeature = (name: string) => {
        const updatedFeatures = data.agent.features.map((f: any) => 
            f.name === name ? { ...f, is_enabled: !f.is_enabled } : f
        );
        setData({
            ...data,
            agent: { ...data.agent, features: updatedFeatures }
        });
    };

    const manageAssets = (path: string) => {
        // Set the override cookie if needed for managing THIS company (brand)
        Cookies.set('company_id_override', data.company.id.toString(), { expires: 1 });
        router.push(path);
    };

    if (loading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-2 text-muted-foreground">{t('platformAgent.loading', 'Cargando...')}</span>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
                <Bot className="h-16 w-16 text-muted-foreground/20" />
                <div className="text-center">
                    <h3 className="text-lg font-semibold">{t('platformAgent.notInitialized', 'Plataforma no inicializada')}</h3>
                    <p className="text-muted-foreground mb-4">{t('platformAgent.initializeDesc', 'Haz clic abajo para crear el registro del agente oficial.')}</p>
                    <Button onClick={() => handleSave()}>{t('platformAgent.initializeBtn', 'Inicializar Agente Aikrofy')}</Button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                        {t('platformAgent.title', 'Agente Oficial de la Marca')}
                    </h1>
                    <p className="text-muted-foreground">
                        {t('platformAgent.description', 'Configura el agente IA que atiende a tus prospectos en la web y vende tus planes.')}
                    </p>
                </div>
                <Button onClick={handleSave} disabled={saving} className="shadow-lg">
                    {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                    {t('common.save')}
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Bot className="h-5 w-5 text-primary" />
                            {t('platformAgent.identity', 'Identidad del Agente')}
                        </CardTitle>
                        <CardDescription>{t('platformAgent.identityDesc', 'Configura la identidad y comportamiento del agente de soporte oficial.')}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="platform-name">{t('platformAgent.companyName', 'Nombre de la Empresa')}</Label>
                                <Input 
                                    id="platform-name" 
                                    value={data.company.name} 
                                    onChange={(e) => setData({...data, company: {...data.company, name: e.target.value}})}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="agent-name">{t('platformAgent.agentName', 'Nombre del Agente')}</Label>
                                <Input 
                                    id="agent-name" 
                                    value={data.agent.name} 
                                    onChange={(e) => setData({...data, agent: {...data.agent, name: e.target.value}})}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="tone">{t('platformAgent.tone', 'Tono de Voz')}</Label>
                                <Select 
                                    value={data.agent.tone} 
                                    onValueChange={(val) => setData({...data, agent: {...data.agent, tone: val}})}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="friendly">{t('platformAgent.toneFriendly', 'Amigable')}</SelectItem>
                                        <SelectItem value="professional">{t('platformAgent.toneProfessional', 'Profesional')}</SelectItem>
                                        <SelectItem value="sales">{t('platformAgent.tonePersuasive', 'Ventas (Persuasivo)')}</SelectItem>
                                        <SelectItem value="support">{t('platformAgent.toneSupport', 'Soporte')}</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="objective">{t('platformAgent.objective', 'Objetivo Principal')}</Label>
                                <Select 
                                    value={data.agent.objective} 
                                    onValueChange={(val) => setData({...data, agent: {...data.agent, objective: val}})}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="sales">{t('platformAgent.objectiveSales', 'Vender Planes')}</SelectItem>
                                        <SelectItem value="lead_qualification">{t('platformAgent.objectiveQualify', 'Calificar Prospectos')}</SelectItem>
                                        <SelectItem value="customer_service">{t('platformAgent.objectiveSupport', 'Atención al Cliente')}</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="system-prompt">{t('platformAgent.systemPrompt', 'Prompt del Sistema (Instrucciones)')}</Label>
                            <Textarea 
                                id="system-prompt" 
                                rows={8}
                                placeholder={t('platformAgent.promptPlaceholder', 'Escribe aquí las instrucciones de venta y soporte...')}
                                value={data.agent.system_prompt || ''} 
                                onChange={(e) => setData({...data, agent: {...data.agent, system_prompt: e.target.value}})}
                                className="italic"
                            />
                            <p className="text-xs text-muted-foreground italic">{t('platformAgent.promptDesc', 'Este prompt define la estrategia de venta y el conocimiento base de la marca.')}</p>
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card className="border-primary/20">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <Zap className="h-4 w-4 text-orange-500" />
                                {t('platformAgent.features', 'Habilidades (Features)')}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {data.agent.features.filter((f: any) => f.category === 'channel' || f.category === 'integration' || f.category === 'tool' || f.category === 'ai_feature').map((feat: any) => (
                                <div key={feat.name} className="flex items-center justify-between">
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium">{feat.label}</span>
                                        <span className="text-[10px] text-muted-foreground uppercase">{feat.category}</span>
                                    </div>
                                    <Switch 
                                        checked={feat.is_enabled} 
                                        onCheckedChange={() => toggleFeature(feat.name)}
                                    />
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    <Card className="bg-primary/5 border-dashed">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <Shield className="h-4 w-4 text-primary" />
                                {t('platformAgent.brandAssets', 'Activos de la Marca')}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="text-xs text-muted-foreground">
                            {t('platformAgent.brandAssetsDesc', 'El Agente Aikrofy tiene acceso a los canales y documentos configurados en este perfil especial.')}
                        </CardContent>
                        <CardFooter className="flex flex-col gap-2">
                            <Button variant="outline" size="sm" className="w-full text-[10px] justify-start" onClick={() => manageAssets('/channels')}>
                                <Globe className="mr-2 h-3 w-3 text-primary" />
                                {t('platformAgent.channelsBtn', 'Configurar Canales Aikrofy')}
                            </Button>
                            <Button variant="outline" size="sm" className="w-full text-[10px] justify-start" onClick={() => manageAssets('/rag')}>
                                <FileText className="mr-2 h-3 w-3 text-secondary" />
                                {t('platformAgent.documentsBtn', 'Gestionar Documentos RAG')}
                            </Button>
                        </CardFooter>
                    </Card>
                </div>
            </div>
        </div>
    );
}
