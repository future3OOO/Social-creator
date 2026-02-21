import { useState, useMemo, useEffect } from "react";
import { useStore } from "../store";

export default function FacebookPreview() {
  const copy = useStore((s) => s.facebookCopy);
  const allImages = useStore((s) => s.images);
  const images = useMemo(() => allImages.filter((img) => img.selected), [allImages]);
  const [idx, setIdx] = useState(0);
  useEffect(() => { if (idx >= images.length) setIdx(Math.max(0, images.length - 1)); }, [images.length]);
  const current = images[idx] ?? images[0];

  return (
    <div className="overflow-hidden rounded-lg bg-white text-[#1c1e21] shadow-lg">
      {/* Header */}
      <div className="flex items-center gap-3 p-3 pb-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-sm font-bold text-white">
          PP
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold">Property Partner</p>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <span>Just now</span>
            <span>·</span>
            <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zM1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0z" />
              <path d="M8 3.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Copy */}
      <div className="px-3 pb-2">
        <p className="whitespace-pre-wrap text-sm leading-snug">{copy}</p>
      </div>

      {/* Image */}
      {current && (
        <div className="relative">
          <img
            src={current.public_url}
            alt="Listing"
            className="w-full object-cover"
            style={{ maxHeight: 500 }}
          />
          {images.length > 1 && (
            <>
              <div className="absolute bottom-3 right-3 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white">
                {idx + 1}/{images.length}
              </div>
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

      {/* Actions */}
      <div className="flex border-t border-gray-200 px-2">
        {["Like", "Comment", "Share"].map((action) => (
          <button
            key={action}
            className="flex flex-1 items-center justify-center gap-2 py-2.5 text-sm font-medium text-gray-500"
          >
            {action === "Like" && (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 .75-.75 2.25 2.25 0 0 1 2.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282m0 0h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 0 1-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 0 0-1.423-.23H5.904m7.72 2.003-1.14.008c-1.627.012-2.864.996-3.26 2.487m0 0H5.904m4.32-2.495H5.904m4.32 0a48.55 48.55 0 0 0-4.32 0m4.32 0v2.495" />
              </svg>
            )}
            {action === "Comment" && (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 0 1-.923 1.785A5.969 5.969 0 0 0 6 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337Z" />
              </svg>
            )}
            {action === "Share" && (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" />
              </svg>
            )}
            {action}
          </button>
        ))}
      </div>
    </div>
  );
}
