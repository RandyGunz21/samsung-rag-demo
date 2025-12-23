/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker multi-stage builds
  output: "standalone",

  // Environment variables that will be available in browser
  env: {
    NEXT_PUBLIC_RAG_SERVICE_URL: process.env.NEXT_PUBLIC_RAG_SERVICE_URL,
    NEXT_PUBLIC_TESTER_SERVICE_URL: process.env.NEXT_PUBLIC_TESTER_SERVICE_URL,
  },
};

export default nextConfig;
