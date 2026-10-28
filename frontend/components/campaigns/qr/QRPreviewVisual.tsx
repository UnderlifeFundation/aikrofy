'use client';

import React, { useEffect, useRef } from 'react';
import QRCodeStyling, { 
    Options, 
    DotType, 
    CornerSquareType, 
    CornerDotType 
} from 'qr-code-styling';

export interface VisualConfig {
    dotsType?: DotType;
    dotsColor?: string;
    cornerSquareType?: CornerSquareType;
    cornerSquareColor?: string;
    cornerDotType?: CornerDotType;
    cornerDotColor?: string;
    backgroundColor?: string;
    logoUrl?: string;
    logoSize?: number;
    logoMargin?: number;
}

interface QRPreviewVisualProps {
    value: string;
    visualConfig?: VisualConfig;
    size?: number;
    className?: string;
}

export const QRPreviewVisual: React.FC<QRPreviewVisualProps> = ({
    value,
    visualConfig = {},
    size = 280,
    className = '',
}) => {
    const ref = useRef<HTMLDivElement>(null);
    const qrCodeRef = useRef<QRCodeStyling | null>(null);

    useEffect(() => {
        const options: Partial<Options> = {
            width: size,
            height: size,
            type: 'svg',
            data: value || 'https://aikrofy.com',
            image: visualConfig.logoUrl || undefined,
            dotsOptions: {
                color: visualConfig.dotsColor || '#1e293b',
                type: (visualConfig.dotsType || 'rounded') as DotType,
            },
            backgroundOptions: {
                color: visualConfig.backgroundColor || '#ffffff',
            },
            cornersSquareOptions: {
                color: visualConfig.cornerSquareColor || visualConfig.dotsColor || '#1e293b',
                type: (visualConfig.cornerSquareType || 'extra-rounded') as CornerSquareType,
            },
            cornersDotOptions: {
                color: visualConfig.cornerDotColor || visualConfig.dotsColor || '#1e293b',
                type: (visualConfig.cornerDotType || 'dot') as CornerDotType,
            },
            imageOptions: {
                crossOrigin: 'anonymous',
                margin: visualConfig.logoMargin ?? 6,
                imageSize: visualConfig.logoSize ?? 0.35,
                hideBackgroundDots: true,
            },
        };

        if (!qrCodeRef.current) {
            qrCodeRef.current = new QRCodeStyling(options);
            if (ref.current) {
                ref.current.innerHTML = '';
                qrCodeRef.current.append(ref.current);
            }
        } else {
            qrCodeRef.current.update(options);
        }
    }, [value, visualConfig, size]);

    return (
        <div className={`relative flex items-center justify-center p-3 rounded-2xl bg-white shadow-sm border border-slate-200 dark:border-slate-800 ${className}`}>
            <div ref={ref} className="qr-container flex items-center justify-center" />
        </div>
    );
};
