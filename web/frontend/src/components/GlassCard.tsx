import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
  premium?: boolean;
}

export default function GlassCard({ children, className = "", premium }: Props) {
  return (
    <div className={`${premium ? "glass-premium" : "glass-card"} gloss-sweep p-5 ${className}`}>
      {children}
    </div>
  );
}
