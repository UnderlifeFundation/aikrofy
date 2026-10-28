'use client';

import Lottie from 'lottie-react';
import { useEffect, useState } from 'react';

interface LottieLoaderProps {
  animationData: any;
  loop?: boolean;
  autoplay?: boolean;
  className?: string;
  width?: number | string;
  height?: number | string;
}

export function LottieLoader({ 
  animationData, 
  loop = true, 
  autoplay = true, 
  className = '',
  width = 200,
  height = 200
}: LottieLoaderProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <Lottie
        animationData={animationData}
        loop={loop}
        autoplay={autoplay}
        style={{ width, height }}
      />
    </div>
  );
}
