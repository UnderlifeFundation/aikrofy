'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { io, Socket } from 'socket.io-client';
import { toast } from 'sonner';

import { ConversationList } from '@/components/chat/omnichannel/ConversationList';
import { ConversationView } from '@/components/chat/omnichannel/ConversationView';
import { ContactProfileSidebar } from '@/components/chat/omnichannel/ContactProfileSidebar';
import ContactDetailsDrawer from '@/app/(dashboard)/contacts/contact-details-drawer';
import apiClient from '@/lib/api-client';
import { Conversation, Message } from '@/types';
import { cn } from '@/lib/utils';

export default function OmnichannelChatPage() {
    const queryClient = useQueryClient();

    // Filters state (Enterprise 10X with Handover)
    const [activeTab, setActiveTab] = useState<'all' | 'handover' | 'customer' | 'employee' | 'resolved'>('all');
    const [selectedChannel, setSelectedChannel] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState<string>('');
    const [debouncedSearch, setDebouncedSearch] = useState<string>('');

    // Selected conversation & CRM drawer
    const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
    const [crmContactId, setCrmContactId] = useState<number | null>(null);
    const [isCrmOpen, setIsCrmOpen] = useState(false);

    // Socket & connection state
    const [socketConnected, setSocketConnected] = useState(false);
    const socketRef = useRef<Socket | null>(null);
    const selectedConversationRef = useRef<Conversation | null>(null);

    useEffect(() => {
        selectedConversationRef.current = selectedConversation;
    }, [selectedConversation]);

    // Debounce search input
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchTerm);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchTerm]);

    // ── 1. Fetch Conversations List ──────────────────────────────────────────
    const {
        data: conversationsData,
        isLoading: isLoadingConversations,
        refetch: refetchConversations,
    } = useQuery({
        queryKey: ['omnichannel-conversations', activeTab, selectedChannel, debouncedSearch],
        queryFn: async () => {
            const params: Record<string, any> = {
                per_page: 50,
            };

            if (activeTab === 'resolved') {
                params.resolved = 'true';
            } else if (activeTab === 'handover') {
                params.handover = 'true';
                params.resolved = 'false';
            } else if (activeTab === 'customer' || activeTab === 'employee') {
                params.type = activeTab;
                params.resolved = 'false';
            } else {
                params.resolved = 'false';
            }

            if (selectedChannel && selectedChannel !== 'all') {
                params.channel = selectedChannel;
            }

            if (debouncedSearch.trim()) {
                params.search = debouncedSearch.trim();
            }

            const res = await apiClient.get('/chat/conversations', { params });
            return res.data?.conversations || [];
        },
        refetchInterval: 10000, // Poll every 10s as backup for realtime
    });

    const conversations: Conversation[] = conversationsData || [];

    // Automatically select the first conversation if none is selected (on desktop screens)
    useEffect(() => {
        if (!selectedConversation && conversations.length > 0) {
            // Only auto-select on desktop (width >= 768px) to allow mobile users to see the list first
            if (typeof window !== 'undefined' && window.innerWidth >= 768) {
                setSelectedConversation(conversations[0]);
            }
        }
    }, [conversations, selectedConversation]);

    // ── 2. Fetch Selected Conversation Messages ──────────────────────────────
    const {
        data: conversationDetails,
        isLoading: isLoadingMessages,
        refetch: refetchMessages,
    } = useQuery({
        queryKey: ['conversation-detail', selectedConversation?.id],
        queryFn: async () => {
            if (!selectedConversation?.id) return null;
            const res = await apiClient.get(`/chat/conversations/${selectedConversation.id}`);
            return res.data?.conversation || null;
        },
        enabled: !!selectedConversation?.id,
    });

    const currentMessages: Message[] = conversationDetails?.messages || [];

    // ── 3. Send Reply Mutation ───────────────────────────────────────────────
    const sendReplyMutation = useMutation({
        mutationFn: async ({ content, pauseAi }: { content: string; pauseAi: boolean }) => {
            if (!selectedConversation?.id) throw new Error('No conversation selected');
            const res = await apiClient.post(`/chat/conversations/${selectedConversation.id}/reply`, {
                content,
                pause_ai: pauseAi,
            });
            return res.data;
        },
        onSuccess: (data) => {
            // Optimistically append message to cache
            if (data.message && selectedConversation?.id) {
                queryClient.setQueryData(
                    ['conversation-detail', selectedConversation.id],
                    (old: any) => {
                        if (!old) return old;
                        const existing = old.messages || [];
                        return {
                            ...old,
                            messages: [...existing, data.message],
                        };
                    }
                );
            }
            refetchConversations();
            if (!data.dispatched) {
                toast.warning('El mensaje fue guardado pero no pudo ser despachado al canal externo.');
            }
        },
        onError: (err: any) => {
            toast.error(err.response?.data?.error || 'Error al enviar el mensaje.');
        },
    });

    // ── 4. Toggle Status / AI Mutation ───────────────────────────────────────
    const updateStatusMutation = useMutation({
        mutationFn: async (payload: { is_resolved?: boolean; is_active?: boolean; is_ai_active?: boolean }) => {
            if (!selectedConversation?.id) throw new Error('No conversation selected');
            const res = await apiClient.patch(
                `/chat/conversations/${selectedConversation.id}/status`,
                payload
            );
            return res.data;
        },
        onSuccess: (data) => {
            if (data.conversation) {
                setSelectedConversation(data.conversation);
            }
            refetchConversations();
            refetchMessages();
            toast.success('Estado actualizado.');
        },
        onError: (err: any) => {
            toast.error(err.response?.data?.error || 'Error al actualizar estado.');
        },
    });

    // ── 5. Socket.IO Realtime Connection ─────────────────────────────────────
    useEffect(() => {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5010/api';
        const socketUrl = API_URL.replace('/api', '');

        const socket = io(socketUrl, {
            path: '/socket.io',
            transports: ['websocket', 'polling'],
        });

        socketRef.current = socket;

        socket.on('connect', () => {
            setSocketConnected(true);
            if (selectedConversationRef.current?.id) {
                socket.emit('join_chat', { conversation_id: selectedConversationRef.current.id });
            }
        });

        socket.on('disconnect', () => {
            setSocketConnected(false);
        });

        socket.on('new_message', (data: any) => {
            const activeConvId = selectedConversationRef.current?.id;
            if (data.conversation_id === activeConvId && data.message) {
                queryClient.setQueryData(
                    ['conversation-detail', activeConvId],
                    (old: any) => {
                        if (!old) return old;
                        const existing = old.messages || [];
                        // Avoid duplicates if message ID already exists
                        if (existing.some((m: Message) => m.id === data.message.id)) {
                            return old;
                        }
                        return {
                            ...old,
                            messages: [...existing, data.message],
                        };
                    }
                );
            }
            refetchConversations();
        });

        socket.on('CONVERSATION_UPDATED', () => {
            refetchConversations();
            refetchMessages();
        });

        return () => {
            socket.disconnect();
        };
    }, [queryClient, refetchConversations, refetchMessages]);

    // When active conversation changes, join its chat room
    useEffect(() => {
        if (socketRef.current && selectedConversation?.id) {
            socketRef.current.emit('join_chat', { conversation_id: selectedConversation.id });
        }
    }, [selectedConversation?.id]);

    // Handlers
    const handleSendMessage = async (content: string, pauseAi: boolean) => {
        await sendReplyMutation.mutateAsync({ content, pauseAi });
    };

    const handleToggleResolved = () => {
        if (!selectedConversation) return;
        updateStatusMutation.mutate({
            is_resolved: !selectedConversation.is_resolved,
        });
    };

    const handleToggleAi = () => {
        if (!selectedConversation) return;
        const currentAiActive = selectedConversation.conv_metadata?.is_ai_active !== false;
        updateStatusMutation.mutate({
            is_ai_active: !currentAiActive,
        });
    };

    const handleOpenCrmDrawer = (customerId: number) => {
        setCrmContactId(customerId);
        setIsCrmOpen(true);
    };

    return (
        <div className="flex h-full w-full overflow-hidden bg-background">
            {/* 1. Left Column: Conversation List with Filters */}
            <div className={cn(
                "w-full md:w-80 lg:w-96 shrink-0 h-full flex flex-col min-h-0",
                selectedConversation ? "hidden md:flex" : "flex"
            )}>
                <ConversationList
                    conversations={conversations}
                    selectedId={selectedConversation?.id || null}
                    onSelect={(conv) => setSelectedConversation(conv)}
                    searchTerm={searchTerm}
                    onSearchChange={setSearchTerm}
                    activeTab={activeTab}
                    onTabChange={(tab: any) => setActiveTab(tab)}
                    selectedChannel={selectedChannel}
                    onChannelChange={setSelectedChannel}
                    isLoading={isLoadingConversations}
                    onRefresh={refetchConversations}
                />
            </div>

            {/* 2. Middle Column: Active Conversation Messages & Reply Box */}
            <div className={cn(
                "flex-1 h-full min-h-0 flex-col min-w-0",
                selectedConversation ? "flex" : "hidden md:flex"
            )}>
                <ConversationView
                    conversation={selectedConversation}
                    messages={currentMessages}
                    isLoadingMessages={isLoadingMessages}
                    onSendMessage={handleSendMessage}
                    isSending={sendReplyMutation.isPending}
                    onToggleResolved={handleToggleResolved}
                    isUpdatingStatus={updateStatusMutation.isPending}
                    onToggleAi={handleToggleAi}
                    onBack={() => setSelectedConversation(null)}
                />
            </div>

            {/* 3. Right Column: 360° Contact Profile & Metrics */}
            <ContactProfileSidebar
                conversation={selectedConversation}
                onOpenCrmDrawer={handleOpenCrmDrawer}
            />

            {/* CRM Drawer Modal */}
            {isCrmOpen && crmContactId && (
                <ContactDetailsDrawer
                    contactId={crmContactId}
                    isOpen={isCrmOpen}
                    onClose={() => setIsCrmOpen(false)}
                    onUpdate={() => {
                        refetchConversations();
                        refetchMessages();
                    }}
                />
            )}
        </div>
    );
}
