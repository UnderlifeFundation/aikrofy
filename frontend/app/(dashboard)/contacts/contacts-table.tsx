'use client';

import { useState, useMemo, useEffect } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    flexRender,
    SortingState,
    ColumnFiltersState,
} from '@tanstack/react-table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getColumns } from './columns';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import apiClient from '@/lib/api-client';
import type { Customer } from '@/types';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { io } from 'socket.io-client';
import { useAuthStore } from '@/store/use-auth-store';

interface ContactsTableProps {
    search: string;
    onContactClick: (id: number) => void;
}

export default function ContactsTable({ search, onContactClick }: ContactsTableProps) {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { user } = useAuthStore();
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

    const { data: customersData, isLoading } = useQuery({
        queryKey: ['contacts', search],
        queryFn: async () => {
            const params = search ? `?search=${encodeURIComponent(search)}` : '';
            const { data } = await apiClient.get<{ data: Customer[] }>(`/customers${params}`);
            return data.data;
        },
        refetchInterval: 5000,
    });

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

        socket.on('LEAD_UPDATED', () => {
            queryClient.invalidateQueries({ queryKey: ['contacts'] });
        });

        return () => {
            socket.disconnect();
        };
    }, [user?.company_id, queryClient]);

    const deleteCustomerMutation = useMutation({
        mutationFn: async (id: number) => {
            return apiClient.delete(`/customers/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['contacts'] });
            toast.success(t('common.success', { defaultValue: 'Contact deleted successfully' }));
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.error || t('common.error', { defaultValue: 'Failed to delete contact' }));
        },
    });

    const columns = useMemo(() => getColumns(t, onContactClick, (customer) => {
        deleteCustomerMutation.mutate(customer.id);
    }), [t, onContactClick]);

    const table = useReactTable({
        data: customersData || [],
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onSortingChange: setSorting,
        getSortedRowModel: getSortedRowModel(),
        onColumnFiltersChange: setColumnFilters,
        getFilteredRowModel: getFilteredRowModel(),
        state: {
            sorting,
            columnFilters,
        },
    });

    return (
        <div className="space-y-4">
            <div className="rounded-md border bg-card">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(header.column.columnDef.header, header.getContext())}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i}>
                                    <TableCell><Skeleton className="h-4 w-[120px]" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-[160px]" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-[100px]" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-[80px]" /></TableCell>
                                    <TableCell><Skeleton className="h-8 w-8 rounded-full" /></TableCell>
                                </TableRow>
                            ))
                        ) : table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow key={row.id}>
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={columns.length} className="h-24 text-center">
                                    {t('contacts.noResults')}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            <div className="flex items-center justify-end space-x-2 py-4">
                <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
                    {t('contacts.previous')}
                </Button>
                <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
                    {t('contacts.next')}
                </Button>
            </div>
        </div>
    );
}
