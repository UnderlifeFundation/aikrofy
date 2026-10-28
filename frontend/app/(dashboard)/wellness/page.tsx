'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Activity,
    Calendar,
    User,
    ArrowRight,
    MoreHorizontal,
    FileText,
    Trash2
} from 'lucide-react';
import { format } from 'date-fns';
import Link from 'next/link';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/use-auth-store';

import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api-client';
import type { WellnessEvaluation } from '@/types';

import { useTranslation } from 'react-i18next';

export default function WellnessPage() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { data: evaluations, isLoading } = useQuery({
        queryKey: ['evaluations'],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: WellnessEvaluation[] }>('/wellness/evaluations');
            return data.data;
        },
    });

    const generatePdfMutation = useMutation({
        mutationFn: async (id: number) => {
            return apiClient.post(`/wellness/evaluations/${id}/pdf`);
        },
        onSuccess: () => {
            toast.success(t('common.success', { defaultValue: 'PDF generation started. Check your details shortly.' }));
        },
        onError: () => {
            toast.error(t('common.error', { defaultValue: 'Failed to trigger PDF generation.' }));
        },
    });

    const deleteEvaluationMutation = useMutation({
        mutationFn: async (id: number) => {
            return apiClient.delete(`/wellness/evaluations/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['evaluations'] });
            toast.success(t('common.success', { defaultValue: 'Evaluation deleted.' }));
        },
        onError: () => {
            toast.error(t('common.error', { defaultValue: 'Failed to delete evaluation.' }));
        },
    });

    const user = useAuthStore((s) => s.user) as any;
    const companyId = user?.company?.tax_id
        || user?.company?.id
        || user?.company_id
        || '';
    const shareUrl = typeof window !== 'undefined' && companyId
        ? `${window.location.origin}/evaluate/${companyId}`
        : '';

    const copyLink = () => {
        if (!shareUrl) {
            toast.error(t('common.error', { defaultValue: 'Company ID not available. Set it in Settings.' }));
            return;
        }
        navigator.clipboard.writeText(shareUrl);
        toast.success(t('common.success', { defaultValue: 'Evaluation link copied to clipboard!' }));
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{t('wellness.title')}</h2>
                    <p className="text-muted-foreground">
                        {t('wellness.description')}
                    </p>
                </div>
                {/* Placeholder for future modal */}
                <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={copyLink} disabled={!companyId}>
                        <FileText className="mr-2 h-4 w-4" /> {t('wellness.copyLink')}
                    </Button>
                    <Button
                        onClick={() => companyId && window.open(`/evaluate/${companyId}`, '_blank')}
                        disabled={!companyId}
                    >
                        <Activity className="mr-2 h-4 w-4" /> {t('wellness.newEvaluation')}
                    </Button>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>{t('wellness.recentEvaluations')}</CardTitle>
                    <CardDescription>{t('wellness.recentEvaluationsDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-12 w-full" />
                            <Skeleton className="h-12 w-full" />
                            <Skeleton className="h-12 w-full" />
                        </div>
                    ) : evaluations?.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
                            <Activity className="mb-2 h-8 w-8 opacity-20" />
                            <p>{t('common.noResults', { defaultValue: 'No evaluations found.' })}</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t('common.date')}</TableHead>
                                    <TableHead>{t('common.contact', { defaultValue: 'Contact' })}</TableHead>
                                    <TableHead>{t('common.goal', { defaultValue: 'Goal' })}</TableHead>
                                    <TableHead>BMI</TableHead>
                                    <TableHead className="text-right">{t('common.actions')}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {evaluations?.map((ev) => (
                                    <TableRow key={ev.id}>
                                        <TableCell className="font-medium">
                                            {format(new Date(ev.created_at), 'MMM d, yyyy')}
                                        </TableCell>
                                        <TableCell>
                                            <Link
                                                href={`/contacts/${ev.lead_id ? 'lead:' + ev.lead_id : 'customer:' + ev.customer_id}`}
                                                className="hover:underline"
                                            >
                                                {(ev as any).contact_name || t('wellness.evaluation') + ' #' + ev.id}
                                            </Link>
                                        </TableCell>
                                        <TableCell>{ev.primary_goal}</TableCell>
                                        <TableCell>
                                            <Badge variant={ev.bmi && ev.bmi > 25 ? 'destructive' : 'outline'}>
                                                {ev.bmi ? ev.bmi.toFixed(1) : 'N/A'}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" className="h-8 w-8 p-0">
                                                        <MoreHorizontal className="h-4 w-4" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuLabel>{t('common.actions')}</DropdownMenuLabel>
                                                    <DropdownMenuItem
                                                        onClick={() => {
                                                            if (ev.pdf_report_path) {
                                                                const url = apiClient.defaults.baseURL + '/wellness/reports/' + ev.pdf_report_path;
                                                                window.open(url, '_blank');
                                                            } else {
                                                                generatePdfMutation.mutate(ev.id);
                                                            }
                                                        }}
                                                    >
                                                        <FileText className="mr-2 h-4 w-4" />
                                                        {ev.pdf_report_path ? t('wellness.viewFullReport') : t('wellness.generatePdf')}
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem asChild>
                                                        <Link href={`/contacts/${ev.lead_id ? 'lead:' + ev.lead_id : 'customer:' + ev.customer_id}`}>
                                                            {t('wellness.viewContact')}
                                                        </Link>
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem
                                                        className="text-destructive focus:text-destructive"
                                                        onClick={() => deleteEvaluationMutation.mutate(ev.id)}
                                                    >
                                                        <Trash2 className="mr-2 h-4 w-4" /> {t('common.delete', { defaultValue: 'Delete' })}
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
