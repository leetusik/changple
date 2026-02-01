import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',

  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'http',
        hostname: '127.0.0.1',
      },
    ],
  },

  // Environment variables (defaults for development)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || '',
  },

  // Disable x-powered-by header
  poweredByHeader: false,

  // Proxy rewrites for development
  async rewrites() {
    const coreUrl = process.env.CORE_SERVICE_URL || 'http://localhost:8000';
    return [
      {
        source: '/media/:path*',
        destination: `${coreUrl}/media/:path*`,
      },
      {
        source: '/api/v1/:path*',
        destination: `${coreUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
