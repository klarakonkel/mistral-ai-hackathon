"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { CharacterState, SkillBranch, AppearanceStage } from "@/types";

// ─── Avatar SVG by appearance stage ──────────────────────────────────────────

const AVATARS: Record<AppearanceStage, React.ReactNode> = {
  egg: (
    <svg viewBox="0 0 80 96" className="w-16 h-16" fill="none">
      <ellipse cx="40" cy="52" rx="28" ry="36" fill="#4f46e5" opacity="0.9" />
      <ellipse cx="40" cy="52" rx="28" ry="36" stroke="#818cf8" strokeWidth="2" />
      <ellipse cx="32" cy="38" rx="5" ry="7" fill="white" opacity="0.25" />
    </svg>
  ),
  hatchling: (
    <svg viewBox="0 0 80 96" className="w-16 h-16" fill="none">
      <ellipse cx="40" cy="56" rx="24" ry="28" fill="#6366f1" />
      <ellipse cx="40" cy="56" rx="24" ry="28" stroke="#a5b4fc" strokeWidth="2" />
      <ellipse cx="40" cy="32" rx="16" ry="16" fill="#7c3aed" />
      <circle cx="34" cy="30" r="3" fill="white" />
      <circle cx="46" cy="30" r="3" fill="white" />
      <circle cx="35" cy="31" r="1.5" fill="#1e1b4b" />
      <circle cx="47" cy="31" r="1.5" fill="#1e1b4b" />
      <path d="M35 38 Q40 42 45 38" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none" />
    </svg>
  ),
  creature: (
    <svg viewBox="0 0 80 96" className="w-16 h-16" fill="none">
      <ellipse cx="40" cy="60" rx="22" ry="26" fill="#7c3aed" />
      <ellipse cx="40" cy="60" rx="22" ry="26" stroke="#c4b5fd" strokeWidth="2" />
      <ellipse cx="40" cy="32" rx="18" ry="18" fill="#6d28d9" />
      <circle cx="33" cy="29" r="4" fill="white" />
      <circle cx="47" cy="29" r="4" fill="white" />
      <circle cx="34" cy="30" r="2" fill="#1e1b4b" />
      <circle cx="48" cy="30" r="2" fill="#1e1b4b" />
      <path d="M34 39 Q40 44 46 39" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none" />
      <path d="M20 22 Q16 14 22 10" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" />
      <path d="M60 22 Q64 14 58 10" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  evolved: (
    <svg viewBox="0 0 80 96" className="w-16 h-16" fill="none">
      <ellipse cx="40" cy="62" rx="20" ry="24" fill="#6d28d9" />
      <ellipse cx="40" cy="62" rx="20" ry="24" stroke="#ddd6fe" strokeWidth="2" />
      <ellipse cx="40" cy="30" rx="20" ry="20" fill="#5b21b6" />
      <circle cx="32" cy="26" r="5" fill="white" />
      <circle cx="48" cy="26" r="5" fill="white" />
      <circle cx="33" cy="27" r="2.5" fill="#1e1b4b" />
      <circle cx="49" cy="27" r="2.5" fill="#1e1b4b" />
      <path d="M33 38 Q40 44 47 38" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M18 20 Q12 10 20 6" stroke="#c4b5fd" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M62 20 Q68 10 60 6" stroke="#c4b5fd" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="40" cy="50" r="3" fill="#ddd6fe" opacity="0.5" />
      <ellipse cx="33" cy="16" rx="4" ry="6" fill="#7c3aed" transform="rotate(-20 33 16)" />
      <ellipse cx="47" cy="16" rx="4" ry="6" fill="#7c3aed" transform="rotate(20 47 16)" />
    </svg>
  ),
  master: (
    <svg viewBox="0 0 80 96" className="w-16 h-16" fill="none">
      <defs>
        <radialGradient id="masterGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#c4b5fd" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#6d28d9" stopOpacity="0" />
        </radialGradient>
      </defs>
      <ellipse cx="40" cy="48" rx="36" ry="44" fill="url(#masterGlow)" />
      <ellipse cx="40" cy="64" rx="18" ry="22" fill="#4c1d95" />
      <ellipse cx="40" cy="64" rx="18" ry="22" stroke="#e9d5ff" strokeWidth="2" />
      <ellipse cx="40" cy="28" rx="22" ry="22" fill="#3b0764" />
      <circle cx="30" cy="24" r="6" fill="white" />
      <circle cx="50" cy="24" r="6" fill="white" />
      <circle cx="31" cy="25" r="3" fill="#1e1b4b" />
      <circle cx="51" cy="25" r="3" fill="#1e1b4b" />
      <circle cx="32" cy="24" r="1" fill="white" />
      <circle cx="52" cy="24" r="1" fill="white" />
      <path d="M32 37 Q40 44 48 37" stroke="white" strokeWidth="2.5" strokeLinecap="round" fill="none" />
      <path d="M16 18 Q8 6 18 2" stroke="#e9d5ff" strokeWidth="3" strokeLinecap="round" />
      <path d="M64 18 Q72 6 62 2" stroke="#e9d5ff" strokeWidth="3" strokeLinecap="round" />
      <polygon points="40,4 43,14 53,14 45,20 48,30 40,24 32,30 35,20 27,14 37,14" fill="#fbbf24" />
    </svg>
  ),
};

const SKILL_LABELS: Record<SkillBranch, string> = {
  communication: "Comms",
  data: "Data",
  creative: "Create",
  scheduling: "Schedule",
  devops: "DevOps",
};

const SKILL_ICONS: Record<SkillBranch, string> = {
  communication: "💬",
  data: "📊",
  creative: "✨",
  scheduling: "🗓",
  devops: "⚙️",
};

interface Props {
  character: CharacterState | null;
}

export default function CharacterPanel({ character }: Props) {
  const prevLevelRef = useRef<number | null>(null);
  const [levelUpFlash, setLevelUpFlash] = useState(false);

  useEffect(() => {
    if (!character) return;
    if (
      prevLevelRef.current !== null &&
      character.level > prevLevelRef.current
    ) {
      setLevelUpFlash(true);
      setTimeout(() => setLevelUpFlash(false), 1200);
    }
    prevLevelRef.current = character.level;
  }, [character?.level]);

  if (!character) {
    return (
      <div className="panel p-4 flex items-center justify-center h-full min-h-[120px]">
        <span className="text-gray-500 text-sm">Loading character…</span>
      </div>
    );
  }

  const xpPct = Math.min(
    100,
    Math.round((character.xp / character.xp_to_next) * 100)
  );

  const skillBranches = Object.entries(character.skills) as [
    SkillBranch,
    { level: number; workflows_completed: number; xp: number }
  ][];

  // Compute total workflows completed across all skill branches
  const totalWorkflowsCompleted = skillBranches.reduce(
    (sum, [, state]) => sum + (state.workflows_completed ?? 0),
    0
  );
  const earnedAchievements = character.achievements.filter((a) => a.earned).length;

  return (
    <div className={`panel p-4 flex flex-col gap-3 ${levelUpFlash ? "level-up-flash" : ""}`}>
      {/* Header row: avatar + name/level */}
      <div className="flex items-center gap-4">
        <motion.div
          key={character.appearance_stage}
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className={`avatar-${character.appearance_stage} shrink-0`}
        >
          {AVATARS[character.appearance_stage as AppearanceStage]}
        </motion.div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-lg truncate">{character.name}</span>
            <AnimatePresence>
              {levelUpFlash && (
                <motion.span
                  key="levelup"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1.3, opacity: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  className="text-yellow-400 text-sm font-bold"
                >
                  LEVEL UP!
                </motion.span>
              )}
            </AnimatePresence>
          </div>

          <div className="flex items-center gap-2 mt-0.5">
            <span className="glow-level text-indigo-400 font-bold text-base">
              Lv.{character.level}
            </span>
            <span className="text-gray-500 text-xs capitalize">
              {character.appearance_stage}
            </span>
          </div>

          {/* XP bar */}
          <div className="mt-2">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>{character.xp.toLocaleString()} XP</span>
              <span>{character.xp_to_next.toLocaleString()} to next level</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="xp-bar-fill h-full rounded-full"
                style={{ width: `${xpPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Greeting + progress summary (right side) */}
        <div className="hidden md:flex flex-col gap-2 shrink-0 max-w-[180px]">
          <div className="character-greeting">
            Hi! I'm Flow-chan. Let's automate something!
          </div>
          <div className="flex gap-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="text-indigo-400 font-bold">{totalWorkflowsCompleted}</span>
              workflows done
            </span>
            <span>·</span>
            <span className="flex items-center gap-1">
              <span className="text-yellow-400 font-bold">{earnedAchievements}</span>
              achievements
            </span>
          </div>
        </div>
      </div>

      {/* Skill branches */}
      <div className="grid grid-cols-5 gap-1.5">
        {skillBranches.map(([branch, state]) => (
          <div
            key={branch}
            className={`skill-badge ${state.level > 0 ? "active" : ""}`}
          >
            <div className="text-base leading-none mb-0.5">
              {SKILL_ICONS[branch]}
            </div>
            <div className="text-gray-300 font-medium leading-none">
              {SKILL_LABELS[branch]}
            </div>
            <div className="text-indigo-400 font-bold leading-none mt-0.5">
              {state.level > 0 ? `Lv${state.level}` : "—"}
            </div>
          </div>
        ))}
      </div>

      {/* Achievements */}
      {character.achievements.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1.5 uppercase tracking-wide">
            Achievements
          </p>
          <div className="flex flex-wrap gap-1.5">
            {character.achievements.map((ach) => (
              <motion.div
                key={ach.id}
                title={`${ach.name}: ${ach.description}`}
                whileHover={{ scale: 1.15 }}
                className={`text-xl cursor-default select-none transition-opacity ${
                  ach.earned ? "opacity-100" : "opacity-25 grayscale"
                }`}
              >
                {ach.icon}
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
