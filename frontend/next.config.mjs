/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The whole point of this project is offline operation. No remote images, no
  // telemetry, no external font fetches (fonts are vendored in public/fonts).
  images: { unoptimized: true },
};

export default nextConfig;
