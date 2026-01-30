'use client';

import { ContentCard } from './content-card';
import type { Content } from '@/types';

interface ContentListProps {
  title: string;
  contents: Content[];
  isLoading?: boolean;
}

export function ContentList({ title, contents, isLoading }: ContentListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2.5 w-full mb-[60px]">
        <div className="flex flex-row items-center w-full h-[30px]">
          <p className="text-xl font-medium text-black m-0">{title}</p>
        </div>
        {/* Loading skeleton */}
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex items-center gap-1 w-full h-fit"
          >
            <div className="w-[26px] h-[26px] min-w-[26px] mx-2 rounded-sm bg-grey-2 animate-pulse" />
            <div className="flex-1 h-[140px] bg-grey-1 rounded-md animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  if (contents.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2.5 w-full mb-[60px]">
      <div className="flex flex-row items-center w-full h-[30px]">
        <p className="text-xl font-medium text-black m-0">{title}</p>
      </div>
      {contents.map((content) => (
        <ContentCard key={content.id} content={content} />
      ))}
    </div>
  );
}
