/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true
  },
  // Add the base path for GitHub Pages
  basePath: process.env.GITHUB_PAGES ? '/Velocitas' : '',
  assetPrefix: process.env.GITHUB_PAGES ? '/Velocitas' : '',
}

module.exports = nextConfig