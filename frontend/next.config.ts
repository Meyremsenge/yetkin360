import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // YET-220: next@16 "next dev" her çalıştığında frontend/AGENTS.md ve
  // frontend/CLAUDE.md oluşturuyor (AI ajanlarına genel next16 notu) — gerçek
  // proje kök CLAUDE.md'siyle karışır, açık kaynak repoda kafa karıştırır.
  agentRules: false,
  // Hide the floating dev-tools "N" badge; it covers the sidebar account card.
  devIndicators: false,
};

export default nextConfig;
