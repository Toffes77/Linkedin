export const MAX_POST_MEDIA_ITEMS = 10;

export function postMediaGrid<T>(items: T[]) {
  return {
    visible: items.slice(0, 4),
    hiddenCount: Math.max(0, items.length - 4),
  };
}

export function carouselIndex(current: number, delta: number, length: number) {
  if (length <= 0) return 0;
  return (current + delta + length) % length;
}
