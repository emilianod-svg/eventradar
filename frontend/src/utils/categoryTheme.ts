import type { CSSProperties } from "react";

type Theme = {
  accent: string;
  accentSoft: string;
  accentInk: string;
  accentWash: string;
};

const THEMES: Array<{ match: RegExp; theme: Theme }> = [
  {
    match: /m[úu]sica|recital|concierto|festival/i,
    theme: {
      accent: "#2563eb",
      accentSoft: "#dbeafe",
      accentInk: "#17315c",
      accentWash: "#eff6ff",
    },
  },
  {
    match: /gastronom|food|feria/i,
    theme: {
      accent: "#d97706",
      accentSoft: "#ffedd5",
      accentInk: "#5a3410",
      accentWash: "#fff7ed",
    },
  },
  {
    match: /teatro|danza|arte|cultura/i,
    theme: {
      accent: "#7c3aed",
      accentSoft: "#ede9fe",
      accentInk: "#3c1d75",
      accentWash: "#f5f3ff",
    },
  },
  {
    match: /deporte|gimnasia|running|torneo/i,
    theme: {
      accent: "#059669",
      accentSoft: "#d1fae5",
      accentInk: "#0f4d38",
      accentWash: "#ecfdf5",
    },
  },
  {
    match: /academ|charla|simposio|congreso/i,
    theme: {
      accent: "#0f766e",
      accentSoft: "#ccfbf1",
      accentInk: "#0b3d3a",
      accentWash: "#f0fdfa",
    },
  },
];

const DEFAULT_THEME: Theme = {
  accent: "#0b5fff",
  accentSoft: "#dbe7ff",
  accentInk: "#17315c",
  accentWash: "#eef4ff",
};

export function getCategoryTheme(category: string | null | undefined): CSSProperties {
  const theme = THEMES.find((entry) => category && entry.match.test(category))?.theme ?? DEFAULT_THEME;

  return {
    ["--event-accent" as never]: theme.accent,
    ["--event-accent-soft" as never]: theme.accentSoft,
    ["--event-accent-ink" as never]: theme.accentInk,
    ["--event-accent-wash" as never]: theme.accentWash,
  } as CSSProperties;
}
