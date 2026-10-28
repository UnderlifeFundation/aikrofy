"use client";

import { useTranslation } from "react-i18next";
import { FileText, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function TermsPage() {
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
                    <FileText className="w-64 h-64" />
                </div>

                <header className="mb-12 border-b pb-8">
                    <h1 className="text-4xl font-bold tracking-tight mb-4 flex items-center gap-3">
                        <FileText className="text-primary w-10 h-10" />
                        {t('legal.termsTitle')}
                    </h1>
                    <p className="text-muted-foreground">
                        {t('legal.lastUpdated', { date: currentDate })}
                    </p>
                </header>

                <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
                    <section>
                        <p className="text-lg leading-relaxed">
                            {t('legal.terms.intro')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.terms.sections.acceptance.title')}</h2>
                        <p>
                            {t('legal.terms.sections.acceptance.content')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.terms.sections.service.title')}</h2>
                        <p>
                            {t('legal.terms.sections.service.content')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.terms.sections.responsibility.title')}</h2>
                        <p>{t('legal.terms.sections.responsibility.content')}</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>{t('legal.terms.sections.responsibility.item1')}</li>
                            <li>{t('legal.terms.sections.responsibility.item2')}</li>
                            <li>{t('legal.terms.sections.responsibility.item3')}</li>
                        </ul>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.terms.sections.payments.title')}</h2>
                        <p>
                            {t('legal.terms.sections.payments.content')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('legal.terms.sections.liability.title')}</h2>
                        <p>
                            {t('legal.terms.sections.liability.content')}
                        </p>
                    </section>

                    <section className="space-y-4 border-t pt-8">
                        <h2 className="text-2xl font-semibold flex items-center gap-2">
                            <span>🔒</span> Protección y Eliminación de Datos de Usuario
                        </h2>
                        <p>
                            Aikrofy respeta el derecho a la privacidad y eliminación de datos de acuerdo con las normativas de Meta / Facebook. Los usuarios pueden solicitar la eliminación permanente de sus credenciales y datos almacenados mediante el mecanismo de Callback de eliminación de datos de Meta (<code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">/api/webhooks/meta-data-deletion</code>) o escribiendo a <a href="mailto:support@aikrofy.com" className="text-primary underline">support@aikrofy.com</a>. Para más detalles consulte nuestra <Link href="/privacy" className="text-primary underline">Política de Privacidad</Link>.
                        </p>
                    </section>


                    <footer className="pt-8 border-t text-sm text-muted-foreground mt-12">
                        {t('legal.privacy.sections.contact.content')}
                    </footer>
                </div>
            </div>
        </div>
    );
}
