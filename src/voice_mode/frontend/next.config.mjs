/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for production builds
  // This creates a self-contained server that doesn't need the full Next.js framework
  output: process.env.BUILD_STANDALONE === 'true' ? 'standalone' : undefined,
  
  // Optimize for production deployment
  trailingSlash: false,
  compress: true,
  
  // Configure static asset serving
  assetPrefix: process.env.ASSET_PREFIX || '',
  
  // Ensure compatibility with Python static file serving
  experimental: {
    outputFileTracingExcludes: {
      '*': [
        'node_modules/@swc/core-linux-x64-gnu',
        'node_modules/@swc/core-linux-x64-musl',
        'node_modules/@esbuild/linux-x64',
      ],
    },
  },
};

export default nextConfig;
