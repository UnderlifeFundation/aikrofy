"use client";

import { useTranslation } from "react-i18next";
import { Shield, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function PrivacyPage() {
    const { t } = useTranslation();
    const currentDate = new Date().toLocaleDateString();

    return (
        <div className="container mx-auto px-4 py-12 max-w-4xl">
            <div className="mb-8">
                <Link href="/">
                    <Button variant="ghost" size="sm" className="gap-2">
                        <ArrowLeft className="w-4 h-4" />
                        {t('common.back')}
                    </Button>
                </Link>
            </div>

            <div className="bg-card border rounded-2xl p-8 md:p-12 shadow-sm relative overflow-hidden">
                {/* Background Decor */}
                <div className="absolute top-0 right-0 p-12 opacity-[0.03] pointer-events-none">
                    <Shield className="w-64 h-64" />
                </div>

                <header className="mb-12 border-b pb-8">
                    <h1 className="text-4xl font-bold tracking-tight mb-4 flex items-center gap-3">
                        <Shield className="text-primary w-10 h-10" />
                        {t('legal.privacyTitle')}
                    </h1>
                    <p className="text-muted-foreground">
                        {t('legal.lastUpdated', { date: currentDate })}
                    </p>
                </header>

                <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
                    <section>
                        <p className="text-lg leading-relaxed">
                            {t('legal.privacy.intro')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.privacy.sections.collection.title')}</h2>
                        <p>{t('legal.privacy.sections.collection.content')}</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>{t('legal.privacy.sections.collection.item1')}</li>
                            <li>{t('legal.privacy.sections.collection.item2')}</li>
                            <li>{t('legal.privacy.sections.collection.item3')}</li>
                        </ul>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.privacy.sections.google.title')}</h2>
                        <p>{t('legal.privacy.sections.google.content')}</p>
                        <div className="bg-primary/5 border border-primary/20 rounded-xl p-6 italic text-sm">
                            {t('legal.privacy.sections.google.disclosure')}
                        </div>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.privacy.sections.use.title')}</h2>
                        <p>{t('legal.privacy.sections.use.content')}</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>{t('legal.privacy.sections.use.item1')}</li>
                            <li>{t('legal.privacy.sections.use.item2')}</li>
                            <li>{t('legal.privacy.sections.use.item3')}</li>
                            <li>{t('legal.privacy.sections.use.item4')}</li>
                        </ul>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.privacy.sections.sovereignty.title')}</h2>
                        <p>
                            {t('legal.privacy.sections.sovereignty.content')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.privacy.sections.thirdParty.title')}</h2>
                        <p>
                            {t('legal.privacy.sections.thirdParty.content')}
                        </p>
                    </section>

                    <section className="space-y-4 border-t pt-8">
                        <h2 className="text-2xl font-semibold flex items-center gap-2">
                            <span>🗑️</span> Eliminación de Datos de Usuario (Meta & Facebook Data Deletion)
                        </h2>
                        <p>
                            De acuerdo con la política de Privacidad y Protección de Datos de Meta (Facebook / WhatsApp API) y el Reglamento General de Protección de Datos (GDPR), los usuarios tienen derecho a solicitar la eliminación de su información personal almacenada en nuestra plataforma.
                        </p>
                        <div className="bg-muted/60 border rounded-xl p-5 space-y-3 text-sm">
                            <h3 className="font-semibold text-foreground">¿Cómo solicitar la eliminación de tus datos?</h3>
                            <ul className="list-disc pl-5 space-y-1.5 text-muted-foreground">
                                <li>
                                    <strong>Desde tu cuenta de Facebook:</strong> Si has conectado Aikrofy mediante Inicio de Sesión con Facebook, puedes desvincular la aplicación ingresando a <em>Facebook &gt; Configuración y privacidad &gt; Configuración &gt; Apps y sitios web</em> y haciendo clic en <strong>Eliminar</strong>.
                                </li>
                                <li>
                                    <strong>Devolución de llamada automatizada (Data Deletion Callback):</strong> Nuestro servidor procesa de manera automatizada la desvinculación a través de la URL de devolución de llamada:
                                    <code className="block mt-1 bg-background p-2 rounded border font-mono text-xs text-foreground break-all">
                                        {typeof window !== 'undefined' ? `${window.location.origin.replace(':3000', ':5010')}/api/webhooks/meta-data-deletion` : 'https://api.aikrofy.com/api/webhooks/meta-data-deletion'}
                                    </code>
                                </li>
                                <li>
                                    <strong>Solicitud Directa:</strong> También puedes solicitar la eliminación completa de tu cuenta, conversaciones y datos asociados enviando un correo electrónico a <a href="mailto:support@aikrofy.com" className="text-primary underline">support@aikrofy.com</a> con el asunto "Solicitud de Eliminación de Datos". Procesaremos tu solicitud en un plazo máximo de 48 horas habiles.
                                </li>
                            </ul>
                        </div>
                    </section>


                    <footer className="pt-8 border-t text-sm text-muted-foreground mt-12">
                        {t('legal.privacy.sections.contact.content')}
                    </footer>
                </div>
            </div>
        </div>
    );
}
