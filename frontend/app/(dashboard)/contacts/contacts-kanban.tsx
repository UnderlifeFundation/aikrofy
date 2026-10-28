'use client';

import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { io } from 'socket.io-client';
import { Mail, Phone } from 'lucide-react';
import Link from 'next/link';
import { useAuthStore } from '@/store/use-auth-store';

interface Stage {
    id: number;
    name: string;
    sort_order: number;
}

interface Customer {
    id: number;
    first_name: string | null;
    last_name: string | null;
    email: string | null;
    phone: string | null;
    lead_score: number;
    funnel_stage_id: number | null;
}

interface ContactsKanbanProps {
    search: string;
    onContactClick: (id: number) => void;
}

export default function ContactsKanban({ search, onContactClick }: ContactsKanbanProps) {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { user } = useAuthStore();

    // 1. Fetch Funnel Stages
    const { data: stages, isLoading: loadingStages } = useQuery<Stage[]>({
        queryKey: ['funnel-stages'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ stages: Stage[] }>('/crm/stages');
            return data.stages;
        }
    });

    // 2. Fetch Customers
    const { data: customers, isLoading: loadingCustomers } = useQuery<Customer[]>({
        queryKey: ['contacts-kanban', search],
        queryFn: async () => {
            const params = search ? `?search=${encodeURIComponent(search)}` : '';
            const { data } = await apiClient.get<{ data: Customer[] }>(`/customers${params}`);
            return data.data;
        }
    });

    // 3. Move Lead Mutation
    const moveLeadMutation = useMutation({
        mutationFn: async ({ customerId, stageId }: { customerId: number; stageId: number | null }) => {
            return apiClient.post('/crm/stages/move', { customer_id: customerId, stage_id: stageId });
        },
        onMutate: async (variables) => {
            await queryClient.cancelQueries({ queryKey: ['contacts-kanban', search] });
            const previousCustomers = queryClient.getQueryData<Customer[]>(['contacts-kanban', search]);
            
            if (previousCustomers) {
                queryClient.setQueryData<Customer[]>(
                    ['contacts-kanban', search],
                    previousCustomers.map(c => c.id === variables.customerId ? { ...c, funnel_stage_id: variables.stageId } : c)
                );
            }
            return { previousCustomers };
        },
        onError: (err, variables, context) => {
            if (context?.previousCustomers) {
                queryClient.setQueryData(['contacts-kanban', search], context.previousCustomers);
            }
            toast.error(t('common.error', { defaultValue: 'Failed to move contact' }));
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['contacts-kanban', search] });
            queryClient.invalidateQueries({ queryKey: ['contacts', search] });
        }
    });

    // 4. WebSocket Sync Listener
    useEffect(() => {
        const socketUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010').replace('/api', '');
        const socket = io(socketUrl, {
            path: '/socket.io',
            transports: ['websocket', 'polling']
        });

        const companyId = user?.company_id;

        socket.on('connect', () => {
            if (companyId) {
                socket.emit('join_company', { company_id: companyId });
            } else {
                socket.emit('join_room', { room: 'company_room_default' });
            }
        });

        socket.on('LEAD_UPDATED', (payload: any) => {
            queryClient.invalidateQueries({ queryKey: ['contacts-kanban', search] });
            queryClient.invalidateQueries({ queryKey: ['contacts', search] });
            toast.info(t('contacts.leadUpdatedByAI', { 
                defaultValue: `Lead updated by AI: Score ${payload.lead_score}`, 
                score: payload.lead_score 
            }));
        });

        return () => {
            socket.disconnect();
        };
    }, [queryClient, search, t, user?.company_id]);

    const handleDragEnd = (result: DropResult) => {
        const { source, destination, draggableId } = result;
        if (!destination) return;

        const sourceStageId = source.droppableId === 'unassigned' ? null : parseInt(source.droppableId);
        const destStageId = destination.droppableId === 'unassigned' ? null : parseInt(destination.droppableId);

        if (sourceStageId === destStageId) return;

        const customerId = parseInt(draggableId);
        moveLeadMutation.mutate({ customerId, stageId: destStageId });
    };

    if (loadingStages || loadingCustomers) {
        return (
            <div className="flex gap-4 p-2 overflow-x-auto">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="w-80 flex-shrink-0 space-y-4">
                        <Skeleton className="h-8 w-1/2 rounded" />
                        <Skeleton className="h-32 w-full rounded-xl" />
                        <Skeleton className="h-32 w-full rounded-xl" />
                    </div>
                ))}
            </div>
        );
    }

    // Include "Unassigned" column for leads that do not have a valid stage_id
    const allStages = stages ? [...stages] : [];
    const validStageIds = new Set(allStages.map(s => s.id));
    const unassignedLeads = (customers || []).filter(c => c.funnel_stage_id === null || !validStageIds.has(c.funnel_stage_id));
    
    return (
        <DragDropContext onDragEnd={handleDragEnd}>
            <div className="flex gap-4 overflow-x-auto pb-4 select-none min-h-[500px]">
                {/* Unassigned column */}
                <div className="w-80 flex-shrink-0 bg-muted/30 rounded-xl p-3 border flex flex-col max-h-[75vh]">
                    <div className="flex justify-between items-center mb-3 px-1">
                        <h3 className="font-semibold text-sm text-foreground flex items-center gap-2">
                            {t('contacts.unassigned', { defaultValue: 'Nuevos / Sin Asignar' })}
                            <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
                                {unassignedLeads.length}
                            </Badge>
                        </h3>
                    </div>
                    <Droppable droppableId="unassigned">
                        {(provided, snapshot) => (
                            <div
                                ref={provided.innerRef}
                                {...provided.droppableProps}
                                className={`flex-1 overflow-y-auto space-y-2.5 min-h-[300px] rounded-lg transition-colors p-1 ${
                                    snapshot.isDraggingOver ? 'bg-accent/40' : ''
                                }`}
                            >
                                {unassignedLeads.map((lead, index) => (
                                    <DraggableCard key={lead.id} lead={lead} index={index} t={t} onContactClick={onContactClick} />
                                ))}
                                {provided.placeholder}
                            </div>
                        )}
                    </Droppable>
                </div>

                {/* Stages columns */}
                {allStages.map(stage => {
                    const stageLeads = (customers || []).filter(c => c.funnel_stage_id === stage.id);
                    return (
                        <div key={stage.id} className="w-80 flex-shrink-0 bg-muted/30 rounded-xl p-3 border flex flex-col max-h-[75vh]">
                            <div className="flex justify-between items-center mb-3 px-1">
                                <h3 className="font-semibold text-sm text-foreground flex items-center gap-2">
                                    {t(`contacts.stages.${stage.name.toLowerCase().replace(/\s+/g, '_')}`, { defaultValue: stage.name })}
                                    <Badge variant="secondary" className="text-[10px] py-0.5 px-1.5">{stageLeads.length}</Badge>
                                </h3>
                            </div>

                            <Droppable droppableId={stage.id.toString()}>
                                {(provided, snapshot) => (
                                    <div
                                        ref={provided.innerRef}
                                        {...provided.droppableProps}
                                        className={`flex-1 overflow-y-auto space-y-2.5 min-h-[300px] rounded-lg transition-colors p-1 ${
                                            snapshot.isDraggingOver ? 'bg-accent/40' : ''
                                        }`}
                                    >
                                        {stageLeads.map((lead, index) => (
                                            <DraggableCard key={lead.id} lead={lead} index={index} t={t} onContactClick={onContactClick} />
                                        ))}
                                        {provided.placeholder}
                                    </div>
                                )}
                            </Droppable>
                        </div>
                    );
                })}
            </div>
        </DragDropContext>
    );
}

function DraggableCard({ lead, index, t, onContactClick }: { lead: Customer; index: number; t: any; onContactClick: (id: number) => void }) {
    const fullName = `${lead.first_name || ''} ${lead.last_name || ''}`.trim() || lead.phone || t('common.unknown');
    return (
        <Draggable draggableId={lead.id.toString()} index={index}>
            {(provided, snapshot) => (
                <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                    className={`block hover:shadow-md transition-shadow duration-200 border-l-4 rounded-lg bg-card text-card-foreground shadow-sm ${
                        lead.lead_score >= 80 ? 'border-l-emerald-500' : lead.lead_score >= 50 ? 'border-l-amber-500' : 'border-l-slate-300'
                    } ${snapshot.isDragging ? 'rotate-1 scale-102 shadow-lg ring-1 ring-primary/10' : ''}`}
                >
                    <Card className="border-0 shadow-none">
                        <CardContent className="p-3.5 space-y-2.5">
                            <div className="flex justify-between items-start gap-2">
                                <button 
                                    onClick={() => onContactClick(lead.id)}
                                    className="font-semibold text-xs text-foreground hover:underline text-left line-clamp-1"
                                >
                                    {fullName}
                                </button>
                                <Badge 
                                    variant={lead.lead_score >= 80 ? 'default' : 'secondary'}
                                    className={`text-[9px] font-bold py-0.5 px-1 ${
                                        lead.lead_score >= 80 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 hover:bg-emerald-200 border-0' : ''
                                    }`}
                                >
                                    {lead.lead_score}
                                </Badge>
                            </div>

                            <div className="space-y-1 text-[10px] text-muted-foreground">
                                {lead.email && <div className="flex items-center gap-1.5 truncate"><Mail className="h-3 w-3 flex-shrink-0" /> {lead.email}</div>}
                                {lead.phone && <div className="flex items-center gap-1.5"><Phone className="h-3 w-3 flex-shrink-0" /> {lead.phone}</div>}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </Draggable>
    );
}
