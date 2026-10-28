'use client';

import {
    MessageSquare,
    Calendar,
    FileText,
    PhoneCall,
    Bot,
    Activity
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import type { UnifiedContact } from '@/types';
import { useTranslation } from 'react-i18next';

interface LeadTimelineProps {
    conversations: UnifiedContact['conversations'];
    appointments: UnifiedContact['appointments'];
    evaluations: UnifiedContact['evaluations'];
    notes: UnifiedContact['notes'];
}

type TimelineEvent = {
    id: string;
    type: 'message' | 'appointment' | 'evaluation' | 'note';
    date: Date;
    title: string;
    description: string;
    icon: React.ElementType;
    color: string;
};

export function LeadTimeline({ conversations, appointments, evaluations, notes }: LeadTimelineProps) {
    const { t } = useTranslation();

    // Flatten and sort events
    const events: TimelineEvent[] = [];

    // 1. Conversations (Messages)
    conversations.forEach((conv) => {
        (conv.messages ?? []).forEach((msg) => {
            events.push({
                id: `msg-${msg.id}`,
                type: 'message',
                date: new Date(msg.created_at),
                title: msg.role === 'user' ? t('timeline.receivedMessage') : t('timeline.sentMessage'),
                description: msg.content,
                icon: msg.role === 'assistant' ? Bot : MessageSquare,
                color: msg.role === 'assistant' ? 'bg-primary/10 text-primary' : 'bg-muted text-foreground',
            });
        });
    });

    // 2. Appointments
    appointments.forEach((apt) => {
        events.push({
            id: `apt-${apt.id}`,
            type: 'appointment',
            date: new Date(apt.start_time),
            title: t('timeline.appointmentScheduled'),
            description: `${apt.title} - ${apt.status}`,
            icon: Calendar,
            color: 'bg-green-100 text-green-700',
        });
    });

    // 3. Evaluations
    evaluations.forEach((evalItem) => {
        let desc = `BMI: ${evalItem.bmi?.toFixed(1) || 'N/A'} - Goal: ${evalItem.primary_goal}`;
        if (evalItem.diagnosis) {
            desc += `\n\nDiagnosis: ${evalItem.diagnosis.substring(0, 150)}${evalItem.diagnosis.length > 150 ? '...' : ''}`;
        }
        
        events.push({
            id: `eval-${evalItem.id}`,
            type: 'evaluation',
            date: new Date(evalItem.created_at),
            title: t('timeline.evaluationCompleted'),
            description: desc,
            icon: Activity,
            color: 'bg-purple-100 text-purple-700',
        });
    });

    // 4. Notes
    (notes || []).forEach((note) => {
        events.push({
            id: `note-${note.id}`,
            type: 'note',
            date: new Date(note.created_at),
            title: t('timeline.noteBy', { author: note.author_name || t('contacts.agent') }),
            description: note.content,
            icon: FileText,
            color: 'bg-yellow-100 text-yellow-700',
        });
    });

    // Sort descending (newest first)
    events.sort((a, b) => b.date.getTime() - a.date.getTime());

    if (events.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
                <MessageSquare className="mb-2 h-8 w-8 opacity-20" />
                <p>{t('timeline.noActivity')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 pl-4">
            {events.map((event, i) => (
                <div key={event.id} className="relative flex gap-4">
                    {/* Vertical Line */}
                    {i !== events.length - 1 && (
                        <div className="absolute left-[19px] top-10 h-full w-px bg-border" />
                    )}

                    {/* Icon */}
                    <div
                        className={cn(
                            'flex h-10 w-10 shrink-0 items-center justify-center rounded-full border shadow-sm',
                            event.color
                        )}
                    >
                        <event.icon className="h-5 w-5" />
                    </div>

                    {/* Content */}
                    <div className="flex-1 pb-8">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold">{event.title}</h4>
                            <time className="text-xs text-muted-foreground">
                                {format(event.date, 'MMM d, h:mm a')}
                            </time>
                        </div>
                        <Card className="mt-2">
                            <CardContent className="p-3 text-sm text-foreground/80 whitespace-pre-wrap">
                                {event.description}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            ))}
        </div>
    );
}

