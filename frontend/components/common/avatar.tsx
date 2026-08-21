import Image from "next/image";
import { mediaUrl } from "@/lib/api";

export function Avatar({ name, src, size = 48, className = "" }: { name: string; src?: string | null; size?: number; className?: string }) {
  const url = mediaUrl(src);
  if (url) return <Image unoptimized src={url} alt={`Foto de ${name}`} width={size} height={size} className={`avatar ${className}`} style={{ width: size, height: size }} />;
  return <span className={`avatar avatar-fallback ${className}`} style={{ width: size, height: size, fontSize: Math.max(13, size * .36) }} aria-label={`Sin foto: ${name}`}>{name.trim().slice(0, 1).toUpperCase()}</span>;
}
