import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "s4.anilist.co",
      },
      {
        protocol: "https",
        hostname: "img.anili.st",
      },
      {
        protocol: "https",
        hostname: "cdn.myanimelist.net",
      },
    ],
  },
}

export default nextConfig
