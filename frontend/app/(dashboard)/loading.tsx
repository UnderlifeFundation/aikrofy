'use client';

import { useTranslation } from 'react-i18next';

export default function Loading() {
  const { t } = useTranslation();
  return (
    <div className="flex h-full w-full items-center justify-center min-h-[300px] p-6">
      <div className="flex items-center gap-3 text-muted-foreground text-xs font-medium bg-muted/30 px-4 py-2 rounded-full border border-border/40 animate-pulse">
        <div className="h-2 w-2 rounded-full bg-primary animate-ping" />
        <span>{t('common.loadingContent', 'Cargando contenido...')}</span>
      </div>
    </div>
  );
}
