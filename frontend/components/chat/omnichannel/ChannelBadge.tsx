import React from 'react';
import { MessageSquare, Phone, Send, Mail, Globe, Bot, Shield, Laptop } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface ChannelBadgeProps {
    channel?: string | null;
    showLabel?: boolean;
    className?: string;
    size?: 'sm' | 'md';
}

export function ChannelBadge({ channel, showLabel = true, className, size = 'sm' }: ChannelBadgeProps) {
    const ch = (channel || 'webchat').toLowerCase();

    const getChannelConfig = () => {
        switch (ch) {
            case 'whatsapp':
                return {
                    label: 'WhatsApp',
                    icon: Phone,
                    bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
                    dot: 'bg-emerald-500',
                };
            case 'telegram':
                return {
                    label: 'Telegram',
                    icon: Send,
                    bg: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
                    dot: 'bg-sky-500',
                };
            case 'email':
                return {
                    label: 'Email',
                    icon: Mail,
                    bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
                    dot: 'bg-amber-500',
                };
            case 'web':
            case 'webchat':
                return {
                    label: 'Webchat',
                    icon: Globe,
                    bg: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
                    dot: 'bg-indigo-500',
                };
            case 'admin_chat':
                return {
                    label: 'Admin',
                    icon: Shield,
                    bg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
                    dot: 'bg-purple-500',
                };
            case 'playground':
                return {
                    label: 'Test',
                    icon: Laptop,
                    bg: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
                    dot: 'bg-slate-500',
                };
            default:
                return {
                    label: ch.toUpperCase(),
                    icon: MessageSquare,
                    bg: 'bg-muted text-muted-foreground border-border',
                    dot: 'bg-muted-foreground',
                };
        }
    };

    const config = getChannelConfig();
    const Icon = config.icon;
    const isSmall = size === 'sm';

    return (
        <span
            className={cn(
                'inline-flex items-center gap-1.5 rounded-full border font-medium transition-colors',
                isSmall ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
                config.bg,
                className
            )}
        >
            <Icon className={cn(isSmall ? 'h-3 w-3' : 'h-3.5 w-3.5', 'shrink-0')} />
            {showLabel && <span>{config.label}</span>}
        </span>
    );
}
