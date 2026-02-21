import { useCallback } from "react";
import { useStore } from "../store";

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

interface EditorProps {
  platform: "facebook" | "instagram";
  value: string;
  onChange: (v: string) => void;
  minWords: number;
  maxWords: number;
}

function Editor({ platform, value, onChange, minWords, maxWords }: EditorProps) {
  const wc = wordCount(value);
  const inRange = wc >= minWords && wc <= maxWords;

  const regenerate = useCallback(async () => {
    const listing = useStore.getState().listing;
    if (!listing) return;
    const resp = await fetch("/api/generate-copy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ listing }),
    });
    if (!resp.ok) return;
    const data = await resp.json();
    onChange(data[platform]);
  }, [platform, onChange]);

  return (
    <div className="flex flex-1 flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          {platform === "facebook" ? "Facebook" : "Instagram"}
        </span>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-medium ${inRange ? "text-brand-400" : "text-amber-400"}`}>
            {wc} words ({minWords}-{maxWords})
          </span>
          <button onClick={regenerate} className="btn-secondary rounded-lg px-3 py-1 text-xs">
            Regenerate
          </button>
        </div>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={8}
        className="input-glass w-full resize-none text-sm leading-relaxed"
      />
    </div>
  );
}

export default function CopyEditor() {
  const fb = useStore((s) => s.facebookCopy);
  const ig = useStore((s) => s.instagramCopy);
  const setFb = useStore((s) => s.setFacebookCopy);
  const setIg = useStore((s) => s.setInstagramCopy);

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
      <Editor platform="facebook" value={fb} onChange={setFb} minWords={80} maxWords={150} />
      <Editor platform="instagram" value={ig} onChange={setIg} minWords={60} maxWords={100} />
    </div>
  );
}
