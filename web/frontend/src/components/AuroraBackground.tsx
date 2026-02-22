/**
 * Three radial gradient blobs drifting on #0A0A0B.
 * Ported from Valua's hero-blooms / dashboard-aurora pattern.
 */
export default function AuroraBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
      {/* Sky bloom — top-left */}
      <div
        className="animate-blob-slow absolute -left-1/4 -top-1/4 h-[60vh] w-[60vh] rounded-full opacity-25 blur-3xl"
        style={{ background: "radial-gradient(circle, #B8E0FF, transparent 70%)" }}
      />
      {/* Lavender bloom — top-right */}
      <div
        className="animate-blob-slow-delayed absolute -right-1/4 top-[10%] h-[50vh] w-[50vh] rounded-full opacity-20 blur-3xl"
        style={{ background: "radial-gradient(circle, #D4B8FF, transparent 70%)" }}
      />
      {/* Teal bloom — bottom-center */}
      <div
        className="animate-blob-slow-delayed-2 absolute bottom-[-10%] left-1/3 h-[45vh] w-[45vh] rounded-full opacity-15 blur-3xl"
        style={{ background: "radial-gradient(circle, #41E0C2, transparent 70%)" }}
      />
    </div>
  );
}
