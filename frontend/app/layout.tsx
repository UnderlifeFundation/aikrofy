import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import './globals.css';
import { Providers } from './providers';
import { HubSpotChatWidget } from '@/components/HubSpotChatWidget';

const inter = Inter({ subsets: ['latin'] });

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export const metadata: Metadata = {
  title: 'Aikrofy — Ecosistema de Agentes IA para Empresas',
  description: 'Optimiza tu fuerza de trabajo con agentes IA 24/7. Automatiza ventas, soporte, cobranzas y agendamiento con el orquestador inteligente de Aikrofy.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <HubSpotChatWidget />
          {/* Global PayPal SDK with Live Credit & Card Gateway Support */}
          <Script
            src="https://www.paypal.com/sdk/js?client-id=BAAHaUaKhWsWq0TTXodULxlOOiK6IkAH93rDl1FvxaCB4EiNVgnRyswgsmPFKUclEPgSRNzblvfHwHJNFA&currency=USD&disable-funding=credit"
            strategy="afterInteractive"
            id="paypal-sdk-script"
          />
        </Providers>
      </body>
    </html>
  );
}
