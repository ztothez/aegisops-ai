import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/health", destination: "http://127.0.0.1:8000/health" },
      { source: "/model-routing", destination: "http://127.0.0.1:8000/model-routing" },
      { source: "/run", destination: "http://127.0.0.1:8000/run" },
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
      { source: "/export/:path*", destination: "http://127.0.0.1:8000/export/:path*" },
      { source: "/topology", destination: "http://127.0.0.1:8000/topology" },
      { source: "/intel/:path*", destination: "http://127.0.0.1:8000/intel/:path*" },
      { source: "/assets/:path*", destination: "http://127.0.0.1:8000/assets/:path*" }
    ];
  }
};

export default nextConfig;
