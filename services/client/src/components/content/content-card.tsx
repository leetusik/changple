"use client";

import Link from "next/link";
import { useContentSelectionStore } from "@/stores/content-selection-store";
import { useUIStore } from "@/stores/ui-store";
import { Check } from "lucide-react";
import type { Content } from "@/types";

interface ContentCardProps {
  content: Content;
}

export function ContentCard({ content }: ContentCardProps) {
  const { selectedIds, toggle } = useContentSelectionStore();
  const { showContentDetails } = useUIStore();
  const isSelected = selectedIds.includes(content.id);

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggle({ id: content.id, title: content.title });
  };

  const handleCardClick = () => {
    // Show content in sidebar without URL change
    showContentDetails(content.id);
  };

  // Use description or summary as the preview text
  const previewText = content.description || content.summary || content.title;
  const thumbnailSrc = content.thumbnail_url;

  // If external URL, use Link; otherwise use button to show in sidebar
  if (content.url) {
    return (
      <div className="flex flex-row items-center w-full h-fit gap-1">
        {/* External link */}
        <Link
          href={content.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 min-w-0 overflow-hidden no-underline"
        >
          <CardContent
            title={content.title}
            previewText={previewText}
            thumbnailSrc={thumbnailSrc}
          />
        </Link>

        {/* Checkbox */}
        <button
          onClick={handleCheckboxClick}
          className={`w-[26px] h-[26px] min-w-[26px] mx-2 rounded-sm border flex-shrink-0 flex items-center justify-center cursor-pointer transition-colors ${
            isSelected
              ? "bg-blue-1 border-grey-2"
              : "bg-white border-grey-3 hover:bg-grey-1"
          }`}
          aria-label={isSelected ? "선택 해제" : "선택"}
        >
          {isSelected && <Check className="w-[18px] h-[18px] text-white" />}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-row items-center w-full h-fit gap-1">
      {/* Card content - show in sidebar without URL change */}
      <button
        onClick={handleCardClick}
        className="flex-1 min-w-0 overflow-hidden text-left"
      >
        <CardContent
          title={content.title}
          previewText={previewText}
          thumbnailSrc={thumbnailSrc}
        />
      </button>

      {/* Checkbox */}
      <button
        onClick={handleCheckboxClick}
        className={`w-[26px] h-[26px] min-w-[26px] mx-2 rounded-sm border flex-shrink-0 flex items-center justify-center cursor-pointer transition-colors ${
          isSelected
            ? "bg-blue-1 border-grey-2"
            : "bg-white border-grey-3 hover:bg-grey-1"
        }`}
        aria-label={isSelected ? "선택 해제" : "선택"}
      >
        {isSelected && <Check className="w-[18px] h-[18px] text-white" />}
      </button>
    </div>
  );
}

interface CardContentProps {
  title: string;
  previewText: string;
  thumbnailSrc: string | null;
}

function CardContent({ title, previewText, thumbnailSrc }: CardContentProps) {
  // Get absolute URL for images (handle both relative and absolute URLs)
  const getAbsoluteUrl = (url: string | null) => {
    if (!url) return null;
    if (url.startsWith("http")) return url; // Already absolute

    // Relative URL - prepend backend URL in development
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
    return backendUrl + url;
  };

  const absoluteThumbnailSrc = getAbsoluteUrl(thumbnailSrc);

  return (
    <div className="flex flex-row items-center justify-start w-full h-[140px] bg-grey-1 rounded-md overflow-hidden hover:bg-btn-hover transition-colors">
      {/* Text area */}
      <div className="flex flex-col justify-center h-[140px] flex-1 min-w-0 max-w-full overflow-hidden mr-2.5 pl-1">
        {/* Title */}
        <h3 className="text-base font-normal mx-2.5 mb-3 whitespace-nowrap overflow-hidden text-ellipsis max-w-full text-black">
          {title}
        </h3>
        {/* Content preview */}
        <p className="text-sm font-light mx-2.5 mb-1 line-clamp-4 leading-[1.4] text-black">
          {previewText}
        </p>
      </div>

      {/* Thumbnail */}
      {absoluteThumbnailSrc && (
        <div className="w-[120px] h-[120px] min-w-[120px] rounded-md overflow-hidden flex-shrink-0 m-2.5 bg-grey-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={absoluteThumbnailSrc}
            alt={title}
            className="w-full h-full object-cover"
          />
        </div>
      )}
    </div>
  );
}
