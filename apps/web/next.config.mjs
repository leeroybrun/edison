/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  output: 'standalone',
  // Transpile workspace packages
  transpilePackages: ['@edison/shared', '@edison/api'],
};

export default nextConfig;
