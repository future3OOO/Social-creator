import { useState } from "react";
import { useStore, type ListingData } from "../store";

/** Consume an SSE stream, calling onEvent for each parsed event. */
async function consumeSSE(
  url: string,
  body: object,
  onEvent: (event: string, data: unknown) => void,
) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop()!;
    for (const part of parts) {
      let event = "message";
      let data = "";
      for (const line of part.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (data) onEvent(event, JSON.parse(data));
    }
  }
}

export default function UrlInput() {
  const [url, setUrl] = useState("");
  const error = useStore((s) => s.error);

  async function run() {
    const trimmed = url.trim();
    if (!trimmed) return;

    if (!trimmed.includes("trademe.co.nz")) {
      useStore.getState().setError("URL must be a trademe.co.nz listing");
      return;
    }

    const s = useStore.getState();
    s.setError(null);
    s.setStage("scraping");
    s.setProgress("Connecting to TradeMe...");

    try {
      // 1. Scrape
      let listing: ListingData | null = null;
      await consumeSSE("/api/scrape", { url: trimmed }, (event, data: Record<string, unknown>) => {
        if (event === "progress") useStore.getState().setProgress((data as { message: string }).message);
        if (event === "complete") listing = (data as { listing: ListingData }).listing;
        if (event === "error") throw new Error((data as { message: string }).message);
      });
      if (!listing) throw new Error("No listing data returned");
      useStore.getState().setListing(listing);

      // 2. Images
      useStore.getState().setStage("processing_images");
      useStore.getState().setProgress("Downloading images...");
      let images: { carousel: { local_path: string; public_url: string; score: number }[] } | null = null;
      await consumeSSE("/api/images", {
        image_urls: listing.images,
        listing_id: listing.listing_id,
      }, (event, data: Record<string, unknown>) => {
        if (event === "progress") useStore.getState().setProgress((data as { message: string }).message);
        if (event === "complete") images = (data as { images: typeof images }).images;
        if (event === "error") throw new Error((data as { message: string }).message);
      });
      if (!images) throw new Error("No images returned");
      useStore.getState().setImages(
        images.carousel.map((img, i) => ({ ...img, selected: i < 10 })),
      );

      // 3. Copy
      useStore.getState().setStage("generating_copy");
      useStore.getState().setProgress("Generating social posts...");
      const copyResp = await fetch("/api/generate-copy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listing }),
      });
      if (!copyResp.ok) throw new Error("Copy generation failed");
      const copy = await copyResp.json();
      useStore.getState().setFacebookCopy(copy.facebook);
      useStore.getState().setInstagramCopy(copy.instagram);

      // 4. Review
      useStore.getState().setStage("review");
    } catch (e) {
      useStore.getState().setError(e instanceof Error ? e.message : "Pipeline failed");
      useStore.getState().setStage("idle");
    }
  }

  return (
    <div>
      <div className="glass-address flex items-center gap-3 px-5 py-3">
        <svg className="h-5 w-5 shrink-0" style={{ color: "var(--text-weak)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m9.07-9.07 1.757-1.757a4.5 4.5 0 0 1 6.364 6.364l-4.5 4.5a4.5 4.5 0 0 1-7.244-1.242" />
        </svg>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Paste TradeMe listing URL..."
          className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-white/40"
          autoFocus
        />
        <button
          onClick={run}
          disabled={!url.trim()}
          className="btn-primary shrink-0 rounded-full px-5 py-2 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Go
        </button>
      </div>
      {error && (
        <p className="mt-3 text-center text-sm text-red-400">{error}</p>
      )}
    </div>
  );
}
