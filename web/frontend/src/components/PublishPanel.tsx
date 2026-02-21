import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { useStore } from "../store";
import GlassCard from "./GlassCard";

export default function PublishPanel() {
  const stage = useStore((s) => s.stage);
  const allImages = useStore((s) => s.images);
  const images = useMemo(() => allImages.filter((i) => i.selected), [allImages]);
  const fbCopy = useStore((s) => s.facebookCopy);
  const igCopy = useStore((s) => s.instagramCopy);
  const publishResults = useStore((s) => s.publishResults);
  const setStage = useStore((s) => s.setStage);
  const setPublishResults = useStore((s) => s.setPublishResults);
  const setError = useStore((s) => s.setError);
  const reset = useStore((s) => s.reset);

  const [publishFb, setPublishFb] = useState(true);
  const [publishIg, setPublishIg] = useState(true);
  const [loading, setLoading] = useState(false);

  async function doPublish() {
    if (!publishFb && !publishIg) return;
    setLoading(true);

    try {
      const resp = await fetch("/api/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          facebook_caption: publishFb ? fbCopy : null,
          instagram_caption: publishIg ? igCopy : null,
          image_urls: images.map((i) => i.public_url),
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Publish failed" }));
        throw new Error(err.detail || "Publish failed");
      }
      setPublishResults(await resp.json());
      setStage("done");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (stage === "done") {
    return (
      <GlassCard premium className="text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
        >
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full" style={{ background: "linear-gradient(180deg, #41E0C2, #30C2A9)" }}>
            <svg className="h-8 w-8" style={{ color: "#071A17" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
          </div>
          <h2 className="mb-2 text-xl font-bold gradient-text">Published!</h2>
          <p className="mb-6 text-sm" style={{ color: "var(--text-muted)" }}>
            Your listing has been posted successfully.
          </p>

          {"facebook" in publishResults && (
            <p className="mb-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Facebook: <span className="text-brand-400">Live</span>
            </p>
          )}
          {"instagram" in publishResults && (
            <p className="mb-4 text-sm" style={{ color: "var(--text-muted)" }}>
              Instagram: <span className="text-brand-400">Live</span>
            </p>
          )}

          <button onClick={reset} className="btn-secondary mt-2 rounded-lg px-6 py-2 text-sm">
            New Listing
          </button>
        </motion.div>
      </GlassCard>
    );
  }

  return (
    <GlassCard premium>
      <h2 className="mb-6 text-center text-xl font-bold gradient-text">Publish</h2>

      <div className="mb-6 flex flex-col gap-4">
        <Toggle label="Facebook" enabled={publishFb} onChange={setPublishFb} />
        <Toggle label="Instagram" enabled={publishIg} onChange={setPublishIg} />
      </div>

      <p className="mb-6 text-center text-sm" style={{ color: "var(--text-muted)" }}>
        {images.length} image{images.length !== 1 && "s"} will be posted
      </p>

      <div className="flex gap-3">
        <button
          onClick={() => setStage("review")}
          className="btn-secondary flex-1 py-2.5 text-sm"
        >
          Back
        </button>
        <button
          onClick={doPublish}
          disabled={loading || (!publishFb && !publishIg)}
          className="btn-primary flex-1 py-2.5 text-sm disabled:opacity-40"
        >
          {loading ? "Publishing..." : "Confirm"}
        </button>
      </div>
    </GlassCard>
  );
}

function Toggle({ label, enabled, onChange }: { label: string; enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between rounded-xl px-4 py-3" style={{ background: "var(--glass)" }}>
      <span className="text-sm font-medium" style={{ color: "var(--text)" }}>{label}</span>
      <button
        role="switch"
        aria-checked={enabled}
        onClick={() => onChange(!enabled)}
        className="relative h-6 w-11 rounded-full transition-colors"
        style={{ background: enabled ? "#41E0C2" : "rgba(255,255,255,0.15)" }}
      >
        <motion.div
          className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow"
          animate={{ left: enabled ? 22 : 2 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      </button>
    </label>
  );
}
