import type { NextConfig } from "next";
const apiOrigin = (
  process.env.API_PROXY_TARGET || "http://127.0.0.1:8000"
).replace(/\/$/, "");
const nextConfig: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
      { source: "/health", destination: `${apiOrigin}/health` },
    ];
  },
};
export default nextConfig;
