'use client';

import React, { useState, useEffect } from 'react';
import { MarkdownRenderer } from './markdown-renderer';

interface TypewriterTextProps {
    text: string;
    speed?: number;
    animate?: boolean;
    onComplete?: () => void;
}

export function TypewriterText({ text, speed = 10, animate = true, onComplete }: TypewriterTextProps) {
    const [displayedText, setDisplayedText] = useState(animate ? '' : text);
    const onCompleteRef = React.useRef(onComplete);

    React.useEffect(() => {
        onCompleteRef.current = onComplete;
    }, [onComplete]);

    useEffect(() => {
        if (!animate) {
            setDisplayedText(text);
            return;
        }

        setDisplayedText('');
        let index = 0;
        const intervalId = setInterval(() => {
            setDisplayedText((prev) => {
                const nextChar = text.charAt(index);
                index++;
                if (index >= text.length) {
                    clearInterval(intervalId);
                    if (onCompleteRef.current) {
                        // Delay slightly to ensure render has finished
                        setTimeout(() => onCompleteRef.current?.(), 50);
                    }
                }
                return prev + nextChar;
            });
        }, speed);

        return () => clearInterval(intervalId);
    }, [text, speed, animate]);

    return <MarkdownRenderer content={displayedText} />;
}
