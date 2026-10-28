import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Aikrofy Community (Open-Core) — Fundación Underlife & WEBLIFETECH',
    description: 'Plataforma comunitaria de comercio electrónico, POS nativo y agentes de IA para microempresarios, artesanos y PyMEs. Versión Open-Core auto-hospedada y Nube subvencionada.',
};

export default function CommunityLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
