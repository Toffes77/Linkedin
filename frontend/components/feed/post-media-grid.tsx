"use client";

import { useState } from "react";
import Image from "next/image";
import { mediaUrl, type PostMedia } from "@/lib/api";
import { postMediaGrid } from "@/lib/post-media";
import { MediaViewer } from "@/components/feed/media-viewer";

export function PostMediaGrid({ items }: { items: PostMedia[] }) {
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);
  const { visible, hiddenCount } = postMediaGrid(items);
  if (!items.length) return null;

  return <>
    <div className={`post-media-grid media-count-${Math.min(visible.length, 4)}`}>
      {visible.map((item, index) => <button type="button" className="post-media-tile" key={item.id} onClick={() => setViewerIndex(index)} aria-label={`Abrir ${item.tipo === "IMAGEN" ? "imagen" : "video"} ${index + 1} de ${items.length}`}>
        {item.tipo === "IMAGEN" ? <Image unoptimized fill sizes="(max-width: 520px) 100vw, 710px" src={mediaUrl(item.ruta) ?? ""} alt=""/> : <><video src={mediaUrl(item.ruta) ?? ""} preload="metadata" muted playsInline aria-hidden="true"/><span className="post-video-badge" aria-hidden="true">▶</span></>}
        {index === 3 && hiddenCount > 0 ? <span className="post-media-more">+{hiddenCount}</span> : null}
      </button>)}
    </div>
    {viewerIndex !== null ? <MediaViewer items={items} index={viewerIndex} onIndexChange={setViewerIndex} onClose={() => setViewerIndex(null)}/> : null}
  </>;
}
