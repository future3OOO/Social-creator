import { useState, useMemo, useEffect } from "react";
import { useStore } from "../store";

export default function InstagramPreview() {
  const copy = useStore((s) => s.instagramCopy);
  const allImages = useStore((s) => s.images);
  const images = useMemo(() => allImages.filter((img) => img.selected), [allImages]);
  const [idx, setIdx] = useState(0);
  useEffect(() => { if (idx >= images.length) setIdx(Math.max(0, images.length - 1)); }, [images.length]);
  const current = images[idx] ?? images[0];

  // Split caption and hashtags
  const hashtagStart = copy.indexOf("#");
  const captionText = hashtagStart > 0 ? copy.slice(0, hashtagStart).trim() : copy;
  const hashtags = hashtagStart > 0 ? copy.slice(hashtagStart) : "";
  const truncated = captionText.length > 125 ? captionText.slice(0, 125) + "..." : captionText;

  return (
    <div className="overflow-hidden rounded-lg bg-white text-[#262626] shadow-lg">
      {/* Header */}
      <div className="flex items-center gap-3 px-3 py-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-xs font-bold text-white">
          PP
        </div>
        <span className="text-sm font-semibold">propertypartner.nz</span>
        <div className="ml-auto">
          <svg className="h-5 w-5 text-gray-800" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="5" r="1.5" />
            <circle cx="12" cy="12" r="1.5" />
            <circle cx="12" cy="19" r="1.5" />
          </svg>
        </div>
      </div>

      {/* Image */}
      {current && (
        <div className="relative">
          <img
            src={current.public_url}
            alt="Listing"
            className="w-full"
          />
          {images.length > 1 && (
            <>
              {idx > 0 && (
                <button onClick={() => setIdx(idx - 1)} className="absolute left-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-full bg-black/50 text-white">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
                </button>
              )}
              {idx < images.length - 1 && (
                <button onClick={() => setIdx(idx + 1)} className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-full bg-black/50 text-white">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                </button>
              )}
            </>
          )}
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center px-3 py-2">
        <div className="flex gap-4">
          {/* Heart */}
          <svg className="h-6 w-6 text-gray-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
          </svg>
          {/* Comment */}
          <svg className="h-6 w-6 text-gray-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 0 1-.923 1.785A5.969 5.969 0 0 0 6 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337Z" />
          </svg>
          {/* Send */}
          <svg className="h-6 w-6 text-gray-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
          </svg>
        </div>
        {/* Carousel dots */}
        {images.length > 1 && (
          <div className="flex flex-1 justify-center gap-1">
            {images.map((_, i) => (
              <div
                key={i}
                className={`h-1.5 w-1.5 rounded-full ${i === idx ? "bg-blue-500" : "bg-gray-300"}`}
              />
            ))}
          </div>
        )}
        {/* Bookmark */}
        <svg className="ml-auto h-6 w-6 text-gray-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z" />
        </svg>
      </div>

      {/* Caption */}
      <div className="px-3 pb-3">
        <p className="text-sm leading-snug">
          <span className="font-semibold">propertypartner.nz </span>
          {truncated}
          {captionText.length > 125 && (
            <span className="text-gray-400"> more</span>
          )}
        </p>
        {hashtags && (
          <p className="mt-1 text-sm text-blue-900/70">{hashtags}</p>
        )}
      </div>
    </div>
  );
}
