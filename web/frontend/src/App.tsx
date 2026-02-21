import { AnimatePresence, motion } from "framer-motion";
import { useStore } from "./store";
import AuroraBackground from "./components/AuroraBackground";
import UrlInput from "./components/UrlInput";
import PipelineProgress from "./components/PipelineProgress";
import ListingReview from "./components/ListingReview";
import PublishPanel from "./components/PublishPanel";

const fade = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
};

export default function App() {
  const stage = useStore((s) => s.stage);
  const error = useStore((s) => s.error);
  const isProcessing = ["scraping", "processing_images", "generating_copy"].includes(stage);
  const isHero = stage === "idle" || isProcessing;

  return (
    <div className="relative min-h-screen">
      <AuroraBackground />
      <div className={`relative z-10 flex min-h-screen flex-col items-center px-4 ${isHero ? "justify-center" : "pt-8"}`}>
        {/* Global error toast */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="fixed top-4 z-50 rounded-lg border border-red-500/20 bg-red-500/10 px-5 py-3 text-sm text-red-400 backdrop-blur-lg"
            >
              {error}
              <button
                onClick={() => useStore.getState().setError(null)}
                className="ml-3 font-bold opacity-60 hover:opacity-100"
              >
                x
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {stage === "idle" && (
            <motion.div key="idle" {...fade} className="w-full max-w-xl">
              <div className="mb-8 text-center">
                <h1 className="mb-2 text-4xl font-bold tracking-tight">
                  <span className="gradient-text">Listing Creator</span>
                </h1>
                <p style={{ color: "var(--text-muted)" }} className="text-lg">
                  Paste a TradeMe URL to generate social posts
                </p>
              </div>
              <UrlInput />
            </motion.div>
          )}

          {isProcessing && (
            <motion.div key="processing" {...fade} className="w-full max-w-lg">
              <PipelineProgress />
            </motion.div>
          )}

          {stage === "review" && (
            <motion.div key="review" {...fade} className="w-full max-w-6xl py-8">
              <ListingReview />
            </motion.div>
          )}

          {(stage === "publishing" || stage === "done") && (
            <motion.div key="publish" {...fade} className="mt-[20vh] w-full max-w-lg">
              <PublishPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
