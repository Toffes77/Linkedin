import type { User } from "@/lib/api";

export const PROFILE_COMPLETION_TOTAL = 2;

type ProfileCompletionUser = Pick<User, "nombre" | "headline" | "ciudad" | "foto_perfil_url">;

export type ProfileCompletion = {
  completed: number;
  hasPhoto: boolean;
};

export function getProfileCompletion(user: ProfileCompletionUser): ProfileCompletion {
  const hasProfileDetails = [user.nombre, user.headline, user.ciudad].every((value) => value.trim().length > 0);
  const hasPhoto = Boolean(user.foto_perfil_url?.trim());

  return { completed: Number(hasProfileDetails) + Number(hasPhoto), hasPhoto };
}

export function profileCompletionSeenKey(userId: number) {
  return `atanes_profile_completion_seen_${userId}`;
}

export function profileCompletionPendingKey(userId: number) {
  return `atanes_profile_completion_pending_${userId}`;
}

export type ProfileCompletionStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type ProfileCompletionCardState = "incomplete" | "completed" | "hidden";

export function shouldShowProfileCompleted(user: ProfileCompletionUser & Pick<User, "id">, storage: ProfileCompletionStorage) {
  const { completed, hasPhoto } = getProfileCompletion(user);
  return hasPhoto
    && completed === PROFILE_COMPLETION_TOTAL
    && storage.getItem(profileCompletionPendingKey(user.id)) === "true"
    && storage.getItem(profileCompletionSeenKey(user.id)) !== "true";
}

export function getProfileCompletionCardState(user: ProfileCompletionUser & Pick<User, "id">, storage: ProfileCompletionStorage): ProfileCompletionCardState {
  if (!getProfileCompletion(user).hasPhoto) return "incomplete";
  return shouldShowProfileCompleted(user, storage) ? "completed" : "hidden";
}

export function markProfileCompletionActionStarted(userId: number, storage: ProfileCompletionStorage) {
  storage.setItem(profileCompletionPendingKey(userId), "true");
}

export function markProfileCompletionShown(userId: number, storage: ProfileCompletionStorage) {
  storage.setItem(profileCompletionSeenKey(userId), "true");
  storage.removeItem(profileCompletionPendingKey(userId));
}
