"use client";

import { useTranslation } from "react-i18next";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function RefundPage() {
    const { t } = useTranslation();
    const currentDate = new Date().toLocaleDateString();

    return (
        <div className="container mx-auto px-4 py-12 max-w-4xl">
            <div className="mb-8">
                <Link href="/">
                    <Button variant="ghost" size="sm" className="gap-2">
                        <ArrowLeft className="w-4 h-4" />
                        {t('common.back', { defaultValue: 'Volver' })}
                    </Button>
                </Link>
            </div>

            <div className="bg-card border rounded-2xl p-8 md:p-12 shadow-sm relative overflow-hidden">
                {/* Background Decor */}
                <div className="absolute top-0 right-0 p-12 opacity-[0.03] pointer-events-none">
                    <RefreshCw className="w-64 h-64 animate-spin-slow" />
                </div>

                <header className="mb-12 border-b pb-8">
                    <h1 className="text-4xl font-bold tracking-tight mb-4 flex items-center gap-3">
                        <RefreshCw className="text-primary w-10 h-10" />
                        {t('refunds.title', 'Política de Reembolso')}
                    </h1>
                    <p className="text-muted-foreground">
                        {t('refunds.lastUpdated', 'Última actualización')}: {currentDate}
                    </p>
                </header>

                <div className="prose prose-slate dark:prose-invert max-w-none space-y-8 text-sm sm:text-base leading-relaxed">
                    <section className="space-y-4">
                        <p className="text-lg">
                            {t('refunds.p1')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('refunds.section1.title')}</h2>
                        <p>
                            {t('refunds.section1.p1')}
                        </p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>{t('refunds.section1.li1')}</li>
                            <li>{t('refunds.section1.li2')}</li>
                        </ul>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('refunds.section2.title')}</h2>
                        <p>
                            {t('refunds.section2.p1')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('refunds.section3.title')}</h2>
                        <p>
                            {t('refunds.section3.p1')}
                        </p>
                        <p>
                            {t('refunds.section3.p2')}
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-2xl font-semibold">{t('refunds.section4.title')}</h2>
                        <p>
                            {t('refunds.section4.p1')}
                        </p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>{t('refunds.section4.li1')}</li>
                            <li>{t('refunds.section4.li2')}</li>
                            <li>{t('refunds.section4.li3')}</li>
                        </ul>
                    </section>

                    <footer className="pt-8 border-t text-sm text-muted-foreground mt-12">
                        {t('refunds.footer')}
                    </footer>
                </div>
            </div>
        </div>
    );
}
