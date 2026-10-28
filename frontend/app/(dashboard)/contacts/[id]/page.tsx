'use client';

import { use, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Phone, Mail, Calendar, MoreVertical, MessageSquare,
    ArrowLeft, Send, Trash2, FileText, CreditCard,
    CalendarCheck, StickyNote, Bot, BotOff, Pencil,
} from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
    DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import apiClient from '@/lib/api-client';

interface TimelineEvent {
    type: 'message' | 'appointment' | 'payment' | 'note';
    id: number;
    timestamp: string;
    content?: string;
    title?: string;
    status?: string;
    role?: string;
    channel?: string;
    is_user?: boolean;
    amount?: number;
    currency?: string;
    description?: string;
    author?: string;
    meet_link?: string;
}

interface ContactNote {
    id: number;
    content: string;
    author_name: string;
    created_at: string;
}

interface ContactData {
    id: number;
    first_name: string;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    status: string;
    is_ai_active: boolean;
    ident_number: string | null;
    city: string | null;
    country: string | null;
    created_at: string;
    timeline: TimelineEvent[];
    activity: {
        total_conversations: number;
        last_active: string | null;
        channels_used: string[];
    };
}

export default function ContactDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [noteContent, setNoteContent] = useState('');
    const [activeTab, setActiveTab] = useState('timeline');

    const { data: contact, isLoading } = useQuery({
        queryKey: ['customer-detail', id],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: ContactData }>(`/customers/${id}`);
            return data.data;
        },
    });

    const addNoteMutation = useMutation({
        mutationFn: async (content: string) => apiClient.post(`/customers/${id}/notes`, { content }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-detail', id] });
            setNoteContent('');
            toast.success(t('common.success'));
        },
        onError: () => toast.error(t('common.error')),
    });

    const toggleAiMutation = useMutation({
        mutationFn: async (isActive: boolean) => apiClient.patch(`/customers/${id}/toggle-ai`, { is_ai_active: isActive }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-detail', id] });
            toast.success(t('common.success'));
        },
        onError: () => toast.error(t('common.error')),
    });
    const deleteCustomerMutation = useMutation({
        mutationFn: async () => {
            return apiClient.delete(`/customers/${id}`);
        },
        onSuccess: () => {
            toast.success(t('common.success'));
            window.location.href = '/contacts';
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error'));
        },
    });

    const [editForm, setEditForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        ident_number: '',
        city: '',
        country: '',
    });
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);

    const updateCustomerMutation = useMutation({
        mutationFn: async (data: any) => apiClient.patch(`/customers/${id}`, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['customer-detail', id] });
            setIsEditDialogOpen(false);
            toast.success(t('common.success'));
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error'));
        },
    });

    const openEditDialog = () => {
        if (contact) {
            setEditForm({
                first_name: contact.first_name || '',
                last_name: contact.last_name || '',
                email: contact.email || '',
                phone: contact.phone || '',
                ident_number: contact.ident_number || '',
                city: contact.city || '',
                country: contact.country || '',
            });
            setIsEditDialogOpen(true);
        }
    };

    if (isLoading) {
        return <div className="space-y-4"><Skeleton className="h-48 w-full" /><Skeleton className="h-96 w-full" /></div>;
    }

    if (!contact) return <div>{t('contacts.notFound')}</div>;

    const initials = `${contact.first_name?.[0] || ''}${contact.last_name?.[0] || ''}`.toUpperCase();
    const fullName = `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || contact.phone || t('contacts.noName');

    const timelineNotes = (contact.timeline || []).filter(e => e.type === 'note');
    const timelineMessages = (contact.timeline || []).filter(e => e.type === 'message');
    const timelineAppointments = (contact.timeline || []).filter(e => e.type === 'appointment');
    const timelinePayments = (contact.timeline || []).filter(e => e.type === 'payment');

    const getEventIcon = (type: string) => {
        switch (type) {
            case 'message': return <MessageSquare className="h-4 w-4 text-blue-500" />;
            case 'appointment': return <CalendarCheck className="h-4 w-4 text-green-500" />;
            case 'payment': return <CreditCard className="h-4 w-4 text-purple-500" />;
            case 'note': return <StickyNote className="h-4 w-4 text-yellow-500" />;
            default: return <FileText className="h-4 w-4" />;
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2">
                <Link href="/contacts">
                    <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
                </Link>
                <h1 className="text-xl font-semibold">{t('contacts.profileTitle')}</h1>
            </div>

            <div className="grid gap-6 lg:grid-cols-12">
                {/* Profile Card */}
                <div className="lg:col-span-4 space-y-6">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex flex-col items-center text-center">
                                <Avatar className="h-24 w-24">
                                    <AvatarFallback className="text-2xl">{initials}</AvatarFallback>
                                </Avatar>
                                <h2 className="mt-4 text-xl font-bold">{fullName}</h2>
                                <Badge variant="secondary" className="mt-2 capitalize">{contact.status}</Badge>

                                <div className="mt-6 w-full space-y-4 text-left">
                                    <div className="flex items-center gap-3 text-sm">
                                        <Mail className="h-4 w-4 text-muted-foreground" />
                                        <span>{contact.email || t('contacts.noEmail')}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-sm">
                                        <Phone className="h-4 w-4 text-muted-foreground" />
                                        <span>{contact.phone || t('contacts.noPhone')}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-sm">
                                        <Calendar className="h-4 w-4 text-muted-foreground" />
                                        <span>{t('contacts.registeredAt', { date: contact.created_at ? format(new Date(contact.created_at), 'PPP') : '—' })}</span>
                                    </div>

                                    <Separator className="my-4" />

                                    <div className="flex items-center justify-between">
                                        <div className="space-y-0.5">
                                            <Label className="text-sm font-medium flex items-center gap-1">
                                                {contact.is_ai_active ? <Bot className="h-4 w-4" /> : <BotOff className="h-4 w-4" />}
                                                {t('contacts.aiResponses')}
                                            </Label>
                                            <p className="text-xs text-muted-foreground">{t('contacts.aiDescription')}</p>
                                        </div>
                                        <Switch
                                            checked={contact.is_ai_active ?? true}
                                            onCheckedChange={(checked) => toggleAiMutation.mutate(checked)}
                                            disabled={toggleAiMutation.isPending}
                                        />
                                    </div>
                                </div>

                                <div className="mt-8 flex w-full gap-2">
                                    <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
                                        <DialogTrigger asChild>
                                            <Button variant="outline" className="flex-1" onClick={openEditDialog}>
                                                <Pencil className="mr-2 h-4 w-4" /> {t('common.edit')}
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent className="sm:max-w-[425px]">
                                            <DialogHeader>
                                                <DialogTitle>{t('contacts.editContact')}</DialogTitle>
                                                <DialogDescription>
                                                    {t('contacts.editDescription')}
                                                </DialogDescription>
                                            </DialogHeader>
                                            <div className="grid gap-4 py-4">
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="space-y-2">
                                                        <Label htmlFor="first_name">{t('contacts.firstName')}</Label>
                                                        <Input 
                                                            id="first_name" 
                                                            value={editForm.first_name} 
                                                            onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <Label htmlFor="last_name">{t('contacts.lastName')}</Label>
                                                        <Input 
                                                            id="last_name" 
                                                            value={editForm.last_name} 
                                                            onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="email">{t('common.email')}</Label>
                                                    <Input 
                                                        id="email" 
                                                        type="email"
                                                        value={editForm.email} 
                                                        onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="phone">{t('common.phone')}</Label>
                                                    <Input 
                                                        id="phone" 
                                                        value={editForm.phone} 
                                                        onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="ident_number">{t('contacts.dni')}</Label>
                                                    <Input 
                                                        id="ident_number" 
                                                        value={editForm.ident_number} 
                                                        onChange={(e) => setEditForm({...editForm, ident_number: e.target.value})}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="space-y-2">
                                                        <Label htmlFor="city">{t('contacts.city')}</Label>
                                                        <Input 
                                                            id="city" 
                                                            value={editForm.city} 
                                                            onChange={(e) => setEditForm({...editForm, city: e.target.value})}
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <Label htmlFor="country">{t('contacts.country')}</Label>
                                                        <Input 
                                                            id="country" 
                                                            value={editForm.country} 
                                                            onChange={(e) => setEditForm({...editForm, country: e.target.value})}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                            <DialogFooter>
                                                <Button 
                                                    type="submit" 
                                                    onClick={() => updateCustomerMutation.mutate(editForm)}
                                                    disabled={updateCustomerMutation.isPending}
                                                >
                                                    {updateCustomerMutation.isPending ? t('common.saving') : t('common.save')}
                                                </Button>
                                            </DialogFooter>
                                        </DialogContent>
                                    </Dialog>

                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button className="flex-1">
                                                <MessageSquare className="mr-2 h-4 w-4" /> {t('contacts.contactBtn')}
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem onClick={() => {
                                                const phone = contact.phone?.replace(/\D/g, '');
                                                if (phone) window.open(`https://wa.me/${phone}`, '_blank');
                                                else toast.error(t('contacts.noPhone'));
                                            }}>WhatsApp</DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => {
                                                if (contact.email) window.location.href = `mailto:${contact.email}`;
                                                else toast.error(t('contacts.noEmail'));
                                            }}>Email</DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem 
                                                className="text-destructive focus:text-destructive"
                                                onClick={() => {
                                                    if (confirm(t('common.confirmDelete'))) {
                                                        deleteCustomerMutation.mutate();
                                                    }
                                                }}
                                            >
                                                <Trash2 className="mr-2 h-4 w-4" /> {t('contacts.deleteContact')}
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Activity Summary */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">{t('contacts.activity')}</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">{t('contacts.conversations')}:</span>
                                <span className="font-bold">{contact.activity?.total_conversations || 0}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">{t('contacts.channels')}:</span>
                                <div className="flex gap-1">{(contact.activity?.channels_used || []).map(ch => (
                                    <Badge key={ch} variant="outline" className="text-xs capitalize">{ch}</Badge>
                                ))}</div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Tabs */}
                <div className="lg:col-span-8">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="timeline">{t('contacts.timeline')}</TabsTrigger>
                            <TabsTrigger value="notes">{t('contacts.notes')}</TabsTrigger>
                        </TabsList>

                        <TabsContent value="timeline" className="mt-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle>{t('contacts.timelineTitle')}</CardTitle>
                                    <CardDescription>{t('contacts.timelineDesc')}</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {(!contact.timeline || contact.timeline.length === 0) ? (
                                        <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-muted-foreground">
                                            <p>{t('contacts.noInteractions')}</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-4">
                                            {contact.timeline.slice(0, 50).map((event, idx) => (
                                                <div key={`${event.type}-${event.id}-${idx}`} className="flex gap-3 items-start">
                                                    <div className="mt-1">{getEventIcon(event.type)}</div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                                                    {event.type === 'message' ? (event.is_user ? t('contacts.client') : t('contacts.agent')) : (t(`contacts.${event.type}`) || event.type)}
                                                                </span>
                                                                {event.channel && (
                                                                    <Badge variant="outline" className="text-[10px] py-0 px-1.5 h-4 capitalize font-medium">
                                                                        {event.channel}
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                            <time className="text-xs text-muted-foreground">
                                                                {format(new Date(event.timestamp), 'dd/MM/yy HH:mm')}
                                                            </time>
                                                        </div>
                                                        <p className="text-sm mt-1 line-clamp-3">
                                                            {event.content || event.title || event.description || `${event.amount} ${event.currency}`}
                                                        </p>
                                                        {event.meet_link && (
                                                            <a href={event.meet_link} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:underline">
                                                                🔗 Google Meet
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="notes" className="mt-6">
                            <div className="space-y-6">
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base">{t('contacts.notes')}</CardTitle>
                                        <CardDescription>{t('contacts.addNote')}</CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="note">{t('contacts.newNote')}</Label>
                                            <Textarea
                                                id="note"
                                                placeholder={t('contacts.notePlaceholder')}
                                                value={noteContent}
                                                onChange={(e) => setNoteContent(e.target.value)}
                                                className="min-h-[100px]"
                                            />
                                        </div>
                                        <Button
                                            onClick={() => addNoteMutation.mutate(noteContent)}
                                            disabled={!noteContent.trim() || addNoteMutation.isPending}
                                            className="w-full sm:w-auto"
                                        >
                                            {addNoteMutation.isPending ? t('common.saving') : <><Send className="mr-2 h-4 w-4" /> {t('contacts.addNote')}</>}
                                        </Button>
                                    </CardContent>
                                </Card>

                                <div className="space-y-4">
                                    {timelineNotes.length === 0 ? (
                                        <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-muted-foreground">
                                            <p>{t('contacts.noNotes')}</p>
                                        </div>
                                    ) : (
                                        timelineNotes.map((note) => (
                                            <Card key={note.id}>
                                                <CardContent className="pt-6">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                                                            {note.author || t('contacts.system')}
                                                        </span>
                                                        <time className="text-xs text-muted-foreground">
                                                            {format(new Date(note.timestamp), 'PPP p')}
                                                        </time>
                                                    </div>
                                                    <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                                                </CardContent>
                                            </Card>
                                        ))
                                    )}
                                </div>
                            </div>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}
