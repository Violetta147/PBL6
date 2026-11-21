import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'STT · Tiếng Việt', description: 'Ứng dụng chuyển giọng nói thành văn bản tiếng Việt.' };
export const viewport: Viewport = { interactiveWidget: 'resizes-content' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="vi"><body>{children}</body></html>;
}
