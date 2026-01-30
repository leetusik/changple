import type { Metadata, Viewport } from 'next';
import { Providers } from '@/components/providers';
import './globals.css';

export const metadata: Metadata = {
  title: '창플 AI - 카페 창업 전문 AI 어시스턴트',
  description: '수만개의 창플 데이터, 이제 검색 말고 질문하세요.',
  keywords: ['창플', '카페 창업', 'AI', '창업 컨설팅'],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
