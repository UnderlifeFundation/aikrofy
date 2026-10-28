'use client';

import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, ArrowUpDown, Phone, Mail, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import type { Customer } from '@/types';
import { TFunction } from 'i18next';

export const getColumns = (
    t: TFunction, 
    onContactClick: (id: number) => void,
    onDelete?: (customer: Customer) => void
): ColumnDef<Customer>[] => [
    {
        accessorKey: 'name',
        header: t('common.name'),
        cell: ({ row }) => {
            const c = row.original;
            let fullName = `${c.first_name || ''} ${c.last_name || ''}`.trim();
            if (!fullName) fullName = c.phone || t('common.unknown');
            return (
                <div className="flex flex-col items-start">
                    <button
                        onClick={() => onContactClick(c.id)}
                        className="font-medium hover:underline text-left text-primary hover:text-primary/80 transition-colors"
                    >
                        {fullName}
                    </button>
                    <span className="text-xs text-muted-foreground">{c.email || c.phone}</span>
                </div>
            );
        },
    },
    {
        accessorKey: 'email',
        header: t('common.email'),
        cell: ({ row }) => <span className="text-sm">{row.original.email || '—'}</span>,
    },
    {
        accessorKey: 'phone',
        header: t('common.phone'),
        cell: ({ row }) => <span className="text-sm">{row.original.phone || '—'}</span>,
    },
    {
        accessorKey: 'status',
        header: t('common.status'),
        cell: ({ row }) => {
            const status = row.original.status || 'new';
            const variant = status === 'qualified' ? 'default' : status === 'converted' ? 'outline' : 'secondary';
            return <Badge variant={variant} className="capitalize">{status}</Badge>;
        },
    },
    {
        id: 'actions',
        cell: ({ row }) => {
            const c = row.original;
            return (
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuLabel>{t('common.actions')}</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => navigator.clipboard.writeText(c.phone || '')}>
                            <Phone className="mr-2 h-4 w-4" /> {t('contacts.copyPhone')}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => navigator.clipboard.writeText(c.email || '')}>
                            <Mail className="mr-2 h-4 w-4" /> {t('contacts.copyEmail')}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => onContactClick(c.id)}>
                            {t('contacts.viewProfile')}
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                            className="text-destructive focus:text-destructive"
                            onClick={() => {
                                if (confirm(t('common.confirmDelete'))) {
                                    onDelete?.(c);
                                }
                            }}
                        >
                            <Trash2 className="mr-2 h-4 w-4" /> {t('common.delete')}
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            );
        },
    },
];
