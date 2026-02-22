import { useRef } from "react";
import { useStore } from "../store";
import GlassCard from "./GlassCard";
import CopyEditor from "./CopyEditor";
import FacebookPreview from "./FacebookPreview";
import InstagramPreview from "./InstagramPreview";

export default function ListingReview() {
  const listing = useStore((s) => s.listing);
  const images = useStore((s) => s.images);
  const toggleImage = useStore((s) => s.toggleImage);
  const reorderImages = useStore((s) => s.reorderImages);
  const setStage = useStore((s) => s.setStage);
  const selectedCount = images.filter((i) => i.selected).length;
  const dragIdx = useRef(-1);

  if (!listing) return null;

  function onDragStart(i: number) {
    dragIdx.current = i;
  }

  function onDragOver(e: React.DragEvent, i: number) {
    e.preventDefault();
    if (dragIdx.current === i) return;
    const reordered = [...images];
    const [moved] = reordered.splice(dragIdx.current, 1);
    reordered.splice(i, 0, moved);
    dragIdx.current = i;
    reorderImages(reordered);
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight gradient-text">{listing.title}</h2>
          <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
            {listing.address} · {listing.price}
          </p>
        </div>
        <button
          onClick={() => setStage("publishing")}
          className="btn-primary px-6 py-2.5 text-sm"
          disabled={selectedCount === 0}
        >
          Publish
        </button>
      </div>

      {/* Image grid — drag to reorder */}
      <GlassCard>
        <h3 className="mb-3 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
          Images ({selectedCount}/10 selected) — drag to reorder
        </h3>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
          {images.map((img, i) => (
            <div
              key={img.public_url}
              draggable
              onDragStart={() => onDragStart(i)}
              onDragOver={(e) => onDragOver(e, i)}
              className="group relative aspect-square cursor-grab overflow-hidden rounded-lg active:cursor-grabbing"
            >
              <img
                src={img.public_url}
                alt={`Photo ${i + 1}`}
                className="h-full w-full object-cover pointer-events-none"
                draggable={false}
              />
              <div className="absolute left-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-black/60 text-[10px] font-bold text-white">
                {i + 1}
              </div>
              <button
                onClick={() => toggleImage(i)}
                className={`absolute inset-0 flex items-center justify-center transition-all ${
                  img.selected
                    ? "bg-brand-500/20 ring-2 ring-inset ring-brand-500"
                    : "bg-black/40 opacity-0 group-hover:opacity-100"
                }`}
              >
                {img.selected && (
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-500">
                    <svg className="h-4 w-4 text-surface-900" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  </div>
                )}
              </button>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Copy editor */}
      <GlassCard>
        <h3 className="mb-3 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
          Post Copy
        </h3>
        <CopyEditor />
      </GlassCard>

      {/* Previews */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            Facebook Preview
          </h3>
          <FacebookPreview />
        </div>
        <div>
          <h3 className="mb-3 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            Instagram Preview
          </h3>
          <InstagramPreview />
        </div>
      </div>
    </div>
  );
}
