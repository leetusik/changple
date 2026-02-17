import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  trailingSlash: true,

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
  },

  // Disable x-powered-by header
  poweredByHeader: false,

  // Proxy rewrites for development
  // Agent SSE endpoints (/chat/{nonce}/stream, /chat/{nonce}/stop) are handled
  // by Next.js route handlers in app/api/ for proper streaming.
  // Using 'fallback' rewrites so they only apply when NO filesystem route
  // (including API route handlers) matches — this lets the stream/stop route
  // handlers take priority over the catch-all proxy to Core.
  async rewrites() {
    const coreUrl = process.env.CORE_SERVICE_URL || 'http://localhost:8000';
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [
        {
          source: '/media/:path*',
          destination: `${coreUrl}/media/:path*`,
        },
        {
          source: '/api/v1/:path*/',
          destination: `${coreUrl}/api/v1/:path*/`,
        },
        {
          source: '/api/v1/:path*',
          destination: `${coreUrl}/api/v1/:path*`,
        },
      ],
    };
  },
};

export default nextConfig;
