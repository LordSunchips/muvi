import type { Tier } from "../types";

export function tierClass(tier: Tier): string {
  if (tier === "loved") return "tier-loved";
  if (tier === "liked") return "tier-liked";
  return "tier-disliked";
}

export function rowTierClass(tier: Tier): string {
  return `row-${tierClass(tier)}`;
}

export function ScoreBadge({ score, tier }: { score: number; tier: Tier }) {
  return <span className={`score-badge ${tierClass(tier)}`}>{score.toFixed(1)}</span>;
}
