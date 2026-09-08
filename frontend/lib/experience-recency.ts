import type { Experience } from "@/lib/api";

export function compareExperiencesByRecency(
  left: Experience,
  right: Experience,
): number {
  const leftCurrent = left.hasta === null;
  const rightCurrent = right.hasta === null;
  if (leftCurrent !== rightCurrent) return leftCurrent ? -1 : 1;

  if (left.hasta !== null && right.hasta !== null) {
    const endComparison = right.hasta.localeCompare(left.hasta);
    if (endComparison !== 0) return endComparison;
  }

  const startComparison = right.desde.localeCompare(left.desde);
  if (startComparison !== 0) return startComparison;
  return right.id - left.id;
}

export function getMostRecentExperience(
  experiences: Experience[],
): Experience | null {
  return experiences.reduce<Experience | null>(
    (mostRecent, experience) => (
      mostRecent === null
      || compareExperiencesByRecency(experience, mostRecent) < 0
        ? experience
        : mostRecent
    ),
    null,
  );
}
