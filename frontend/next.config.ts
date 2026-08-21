import type { NextConfig } from "next";

const backendTarget =
  process.env.BACKEND_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV !== "development") {
      return [];
    }
    return [
      { source: "/health", destination: `${backendTarget}/health` },
      { source: "/v1/:path*", destination: `${backendTarget}/v1/:path*` },
    ];
  },
};

export default nextConfig;
