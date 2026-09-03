"use client";

import Link from "next/link";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { CommentForm } from "@/components/feed/comment-form";
import { type Comment, type User } from "@/lib/api";
import { formatRelativeDate } from "@/lib/format";

export function CommentItem({ comment, depth, currentUser, replying, responsesOpen, onReplyingChange, onReply, onDelete, onToggleResponses }: {
  comment: Comment;
  depth: number;
  currentUser: User;
  replying: boolean;
  responsesOpen: boolean;
  onReplyingChange: (open: boolean) => void;
  onReply: (content: string) => Promise<void>;
  onDelete: () => Promise<void>;
  onToggleResponses: () => void;
}) {
  const isReply = depth > 0;
  const isAuthor = comment.usuario_id === currentUser.id;
  const responsesId = `comment-responses-${comment.id}`;

  return <div className={`comment-thread${isReply ? " nested" : ""}`} style={{ marginLeft: `${Math.min(depth, 6) * 18}px` }}>
    <div className={isReply ? "reply-item" : "comment-item"}>
      <Link href={`/perfil/${comment.autor.id}`} className="comment-avatar-link"><Avatar name={comment.autor.nombre} src={comment.autor.foto_perfil_url} size={isReply ? 30 : 36}/></Link>
      <div className="comment-content">
        <div className="comment-bubble">
          <div className="comment-heading"><div><Link href={`/perfil/${comment.autor.id}`}><strong>{comment.autor.nombre}</strong></Link>{comment.autor.headline && <span>{comment.autor.headline}</span>}</div><small>{formatRelativeDate(comment.fecha)}</small></div>
          <p>{comment.contenido}</p>
        </div>
        <div className="comment-actions">
          <button type="button" onClick={() => onReplyingChange(!replying)}>Responder</button>
          {comment.cantidad_respuestas > 0 && <button type="button" className="comment-replies-toggle" onClick={onToggleResponses} aria-expanded={responsesOpen} aria-controls={responsesId}>Respuestas: {comment.cantidad_respuestas}<Icon name="responses-arrow" className="comment-replies-arrow"/></button>}
          {isAuthor && <button type="button" className="comment-delete" onClick={() => void onDelete()}><Icon name="trash"/>Eliminar</button>}
        </div>
        {replying && (
          <CommentForm
            currentUser={currentUser}
            compact
            placeholder="Escribe una respuesta..."
            submitLabel="Responder"
            onSubmit={async (content) => {
              await onReply(content);
              onReplyingChange(false);
            }}
          />
        )}
      </div>
    </div>
  </div>;
}
