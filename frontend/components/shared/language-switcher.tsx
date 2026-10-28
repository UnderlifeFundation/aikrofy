'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const languages = [
    { code: 'en', label: 'English', flag: 'us' },
    { code: 'es', label: 'Español', flag: 'es' },
    { code: 'pt', label: 'Português', flag: 'br' },
    { code: 'de', label: 'Deutsch', flag: 'de' },
    { code: 'fr', label: 'Français', flag: 'fr' },
];

export function LanguageSwitcher() {
    const { i18n } = useTranslation();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const changeLanguage = (lng: string) => {
        i18n.changeLanguage(lng);
        try {
            localStorage.setItem('i18nextLng', lng);
        } catch (e) {
            console.warn('Unable to write to localStorage:', e);
        }
    };

    const currentLang = languages.find((l) => l.code === i18n.language) || languages[0];

    if (!mounted) {
        return (
            <Button variant="ghost" className="h-9 w-9 p-0 flex items-center justify-center rounded-xl animate-pulse" disabled>
                <div className="w-5 h-5 rounded-full bg-muted" />
            </Button>
        );
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-9 w-9 p-0 flex items-center justify-center hover:bg-accent rounded-xl" title={currentLang.label}>
                    <img 
                        src={`https://flagcdn.com/w80/${currentLang.flag}.png`} 
                        alt={currentLang.label}
                        className="w-5 h-5 rounded-full object-cover shrink-0 border border-muted-foreground/20"
                    />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                {languages.map((lang) => (
                    <DropdownMenuItem
                        key={lang.code}
                        onClick={() => changeLanguage(lang.code)}
                        className={i18n.language === lang.code ? 'bg-accent' : ''}
                    >
                        <img 
                            src={`https://flagcdn.com/w80/${lang.flag}.png`} 
                            alt={lang.label}
                            className="w-4 h-4 rounded-full object-cover mr-2.5 shrink-0 border border-muted-foreground/20"
                        />
                        {lang.label}
                    </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
