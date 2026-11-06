import type { NextConfig } from 'next';

const config: NextConfig = {
  poweredByHeader: false,
  // This milestone is local-only. LAN control/authentication is a later gate.
  async headers() {
    return [{ source: '/(.*)', headers: [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'no-referrer' },
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'Permissions-Policy', value: 'microphone=(), camera=()' },
    ] }];
  },
};
export default config;
