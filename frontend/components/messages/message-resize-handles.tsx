"use client";

import type { PointerEvent } from "react";

export type MessageResizeDirection = "width" | "height" | "both";

export function MessageResizeHandles({
  onResizeStart,
}: {
  onResizeStart: (direction: MessageResizeDirection, event: PointerEvent<HTMLButtonElement>) => void;
}) {
  return <div className="message-resize-handles" aria-hidden="true">
    <button type="button" className="message-resize-handle top" tabIndex={-1} onPointerDown={(event) => onResizeStart("height", event)}/>
    <button type="button" className="message-resize-handle left" tabIndex={-1} onPointerDown={(event) => onResizeStart("width", event)}/>
    <button type="button" className="message-resize-handle corner" tabIndex={-1} onPointerDown={(event) => onResizeStart("both", event)}/>
  </div>;
}
