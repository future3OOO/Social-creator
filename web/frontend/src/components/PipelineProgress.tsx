import { motion } from "framer-motion";
import { useStore, type PipelineStage } from "../store";
import GlassCard from "./GlassCard";

const STEPS = [
  { key: "scraping", label: "Scrape", icon: "M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5a17.92 17.92 0 0 1-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" },
  { key: "processing_images", label: "Images", icon: "m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" },
  { key: "generating_copy", label: "Copy", icon: "M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" },
  { key: "review", label: "Review", icon: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

function stepState(stepKey: StepKey, current: PipelineStage) {
  const order: readonly string[] = STEPS.map((s) => s.key);
  const ci = order.indexOf(current);
  const si = order.indexOf(stepKey);
  if (ci < 0) return "pending";
  if (si < ci) return "done";
  if (si === ci) return "active";
  return "pending";
}

export default function PipelineProgress() {
  const stage = useStore((s) => s.stage);
  const progress = useStore((s) => s.progress);

  return (
    <GlassCard premium className="py-8">
      <div className="flex flex-col items-center gap-6">
        {STEPS.map((step, i) => {
          const state = stepState(step.key, stage);
          return (
            <div key={step.key} className="flex w-full flex-col items-center">
              <div className="flex items-center gap-4">
                {/* Icon circle */}
                <motion.div
                  className="flex h-10 w-10 items-center justify-center rounded-full"
                  style={{
                    background: state === "done"
                      ? "linear-gradient(180deg, #41E0C2, #30C2A9)"
                      : state === "active"
                        ? "rgba(65, 224, 194, 0.15)"
                        : "rgba(255, 255, 255, 0.06)",
                    border: state === "active"
                      ? "1.5px solid rgba(65, 224, 194, 0.5)"
                      : "1px solid rgba(255, 255, 255, 0.1)",
                  }}
                  animate={state === "active" ? { scale: [1, 1.05, 1] } : {}}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  {state === "done" ? (
                    <svg className="h-5 w-5" style={{ color: "#071A17" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  ) : (
                    <svg
                      className="h-5 w-5"
                      style={{ color: state === "active" ? "#41E0C2" : "var(--text-weak)" }}
                      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d={step.icon} />
                    </svg>
                  )}
                </motion.div>

                {/* Label */}
                <span
                  className="text-sm font-medium"
                  style={{
                    color: state === "done" ? "#41E0C2"
                      : state === "active" ? "var(--text)"
                        : "var(--text-weak)",
                  }}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line */}
              {i < STEPS.length - 1 && (
                <div className="my-2 h-6 w-px" style={{
                  background: state === "done" || state === "active"
                    ? "rgba(65, 224, 194, 0.3)"
                    : "rgba(255, 255, 255, 0.08)",
                }}>
                  {state === "active" && <div className="light-trail h-full w-full" />}
                </div>
              )}
            </div>
          );
        })}

        {/* Progress message */}
        <motion.p
          key={progress}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-2 text-center text-sm"
          style={{ color: "var(--text-muted)" }}
        >
          {progress}
        </motion.p>
      </div>
    </GlassCard>
  );
}
