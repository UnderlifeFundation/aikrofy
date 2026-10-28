import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 31536000,
  },
  async headers() {
    return [
      {
        source: '/widget.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate, max-age=0',
          },
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/:path*',
        headers: [
          {
            key: 'Vary',
            value: 'Accept, RSC, Next-Router-State-Tree, Next-Router-Prefetch',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
