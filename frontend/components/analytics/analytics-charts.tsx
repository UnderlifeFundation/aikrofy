'use client';

import React from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend,
    BarChart,
    Bar,
} from 'recharts';

// ═══════════════════════════════════════════
// 1. Conversation Timeline (Area Chart)
// ═══════════════════════════════════════════

interface DailyData {
    date: string;
    count: number;
}

interface TimelineProps {
    data: DailyData[];
    loading?: boolean;
}

const GRADIENT_ID = 'conversationGradient';

export function ConversationTimeline({ data, loading }: TimelineProps) {
    if (loading) {
        return (
            <div className="flex h-[300px] items-center justify-center">
                <div className="animate-pulse space-y-3 w-full px-4">
                    <div className="h-4 bg-muted rounded w-1/3" />
                    <div className="h-[250px] bg-muted/40 rounded-lg" />
                </div>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="flex h-[300px] items-center justify-center text-muted-foreground">
                <div className="text-center">
                    <p className="text-sm">No conversation data in this period.</p>
                    <p className="text-xs mt-1 opacity-60">Start receiving messages to see trends.</p>
                </div>
            </div>
        );
    }

    // Format dates for display
    const formattedData = data.map(d => ({
        ...d,
        label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }));

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                    <linearGradient id={GRADIENT_ID} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(250, 90%, 65%)" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="hsl(250, 90%, 65%)" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
                <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11 }}
                    className="fill-muted-foreground"
                    tickLine={false}
                    axisLine={false}
                />
                <YAxis
                    tick={{ fontSize: 11 }}
                    className="fill-muted-foreground"
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                />
                <Tooltip
                    contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '13px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    }}
                    labelStyle={{ color: 'hsl(var(--foreground))', fontWeight: 600 }}
                    itemStyle={{ color: 'hsl(var(--muted-foreground))' }}
                />
                <Area
                    type="monotone"
                    dataKey="count"
                    name="Conversations"
                    stroke="hsl(250, 90%, 65%)"
                    strokeWidth={2.5}
                    fill={`url(#${GRADIENT_ID})`}
                    animationDuration={1200}
                    dot={false}
                    activeDot={{ r: 5, strokeWidth: 2, fill: 'hsl(250, 90%, 65%)' }}
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}

// ═══════════════════════════════════════════
// 2. Sentiment Distribution (Pie Chart)
// ═══════════════════════════════════════════

interface SentimentData {
    positive: number;
    neutral: number;
    negative: number;
}

interface SentimentPieProps {
    data: SentimentData;
    avgScore: number;
    loading?: boolean;
}

const SENTIMENT_COLORS = ['#22c55e', '#64748b', '#ef4444']; // green, slate, red

export function SentimentPieChart({ data, avgScore, loading }: SentimentPieProps) {
    if (loading) {
        return (
            <div className="flex h-[280px] items-center justify-center">
                <div className="animate-pulse h-40 w-40 rounded-full bg-muted" />
            </div>
        );
    }

    const total = data.positive + data.neutral + data.negative;

    if (total === 0) {
        return (
            <div className="flex h-[280px] items-center justify-center text-muted-foreground">
                <div className="text-center">
                    <p className="text-sm">No sentiment data available.</p>
                    <p className="text-xs mt-1 opacity-60">Sentiment is analyzed as conversations happen.</p>
                </div>
            </div>
        );
    }

    const pieData = [
        { name: 'Positive', value: data.positive },
        { name: 'Neutral', value: data.neutral },
        { name: 'Negative', value: data.negative },
    ].filter(d => d.value > 0);

    const sentimentLabel = avgScore > 0.3 ? 'Positive' : avgScore < -0.3 ? 'Negative' : 'Neutral';
    const sentimentColor = avgScore > 0.3 ? 'text-green-500' : avgScore < -0.3 ? 'text-red-500' : 'text-slate-400';

    return (
        <div className="relative">
            <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                    <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={4}
                        dataKey="value"
                        animationDuration={800}
                        strokeWidth={0}
                    >
                        {pieData.map((entry, index) => {
                            const colorIndex = entry.name === 'Positive' ? 0 : entry.name === 'Neutral' ? 1 : 2;
                            return <Cell key={entry.name} fill={SENTIMENT_COLORS[colorIndex]} />;
                        })}
                    </Pie>
                    <Legend
                        verticalAlign="bottom"
                        iconType="circle"
                        iconSize={8}
                        formatter={(value: string) => (
                            <span className="text-xs text-muted-foreground ml-1">{value}</span>
                        )}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                            fontSize: '13px',
                        }}
                        formatter={(value: any, name: any) => [
                            `${value} (${total > 0 ? ((Number(value) / total) * 100).toFixed(0) : 0}%)`,
                            name,
                        ]}
                    />
                </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ marginBottom: 30 }}>
                <div className="text-center">
                    <div className={`text-2xl font-bold ${sentimentColor}`}>
                        {(avgScore * 100).toFixed(0)}%
                    </div>
                    <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{sentimentLabel}</div>
                </div>
            </div>
        </div>
    );
}

// ═══════════════════════════════════════════
// 3. Channel Distribution (Bar Chart)
// ═══════════════════════════════════════════

interface ChannelData {
    channel: string;
    count: number;
}

interface ChannelBarProps {
    data: ChannelData[];
    loading?: boolean;
}

const CHANNEL_COLORS: Record<string, string> = {
    whatsapp: '#25D366',
    webchat: '#6366f1',
    voice: '#f59e0b',
    email: '#3b82f6',
    sms: '#8b5cf6',
    telegram: '#0088cc',
    admin_chat: '#64748b',
};

export function ChannelDistributionChart({ data, loading }: ChannelBarProps) {
    if (loading) {
        return (
            <div className="flex h-[280px] items-center justify-center">
                <div className="animate-pulse space-y-2 w-full px-4">
                    {[80, 60, 40, 20].map((w, i) => (
                        <div key={i} className="h-8 bg-muted rounded" style={{ width: `${w}%` }} />
                    ))}
                </div>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="flex h-[280px] items-center justify-center text-muted-foreground">
                <div className="text-center">
                    <p className="text-sm">No channel data available.</p>
                    <p className="text-xs mt-1 opacity-60">Connect channels and start messaging.</p>
                </div>
            </div>
        );
    }

    const formattedData = data.map(d => ({
        ...d,
        label: d.channel.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        fill: CHANNEL_COLORS[d.channel] || '#94a3b8',
    }));

    return (
        <ResponsiveContainer width="100%" height={280}>
            <BarChart data={formattedData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border/30" horizontal={false} />
                <XAxis
                    type="number"
                    tick={{ fontSize: 11 }}
                    className="fill-muted-foreground"
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                />
                <YAxis
                    type="category"
                    dataKey="label"
                    width={100}
                    tick={{ fontSize: 12 }}
                    className="fill-muted-foreground"
                    tickLine={false}
                    axisLine={false}
                />
                <Tooltip
                    contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '13px',
                    }}
                    formatter={(value: any) => [`${value} conversations`, 'Count']}
                    cursor={{ fill: 'hsl(var(--muted)/0.3)' }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} animationDuration={1000}>
                    {formattedData.map((entry, index) => (
                        <Cell key={index} fill={entry.fill} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}
