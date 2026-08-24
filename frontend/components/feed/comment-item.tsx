"use client";

import Link from "next/link";
import { useState } from "react";
import { Avatar } from "@/components/common/avatar";
import { Icon } from "@/components/common/icons";
import { CommentForm } from "@/components/feed/comment-form";
import { type Comment, type User } from "@/lib/api";
import { formatRelativeDate } from "@/lib/format";

type SharedCommentProps = {
  currentUser: User;
  replyingTo: number | null;
  setReplyingTo: (id: number | null) => void;
  onReply: (commentId: number, content: string) => Promise<void>;
  onDelete: (comment: Comment) => Promise<void>;
};

type CommentBodyProps = SharedCommentProps & {
  comment: Comment;
  isReply: boolean;
  responseCount: number;
  responsesOpen: boolean;
  responsesId: string;
  onToggleResponses: () => void;
};

function CommentBody({ comment, currentUser, isReply, onReply, onDelete, replyingTo, setReplyingTo, responseCount, responsesOpen, responsesId, onToggleResponses }: CommentBodyProps) {
  const isAuthor = comment.usuario_id === currentUser.id;
  return <div className={isReply ? "reply-item" : "comment-item"}>
    <Link href={`/perfil/${comment.autor.id}`} className="comment-avatar-link"><Avatar name={comment.autor.nombre} src={comment.autor.foto_perfil_url} size={isReply ? 30 : 36}/></Link>
    <div className="comment-content">
      <div className="comment-bubble">
        <div className="comment-heading">
          <div><Link href={`/perfil/${comment.autor.id}`}><strong>{comment.autor.nombre}</strong></Link>{comment.autor.headline && <span>{comment.autor.headline}</span>}</div>
          <small>{formatRelativeDate(comment.fecha)}</small>
        </div>
        <p>{comment.contenido}</p>
      </div>
      <div className="comment-actions">
        <button type="button" onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}>Responder</button>
        {responseCount > 0 && <button type="button" className="comment-replies-toggle" onClick={onToggleResponses} aria-expanded={responsesOpen} aria-controls={responsesId}>Respuestas: {responseCount}<Icon name="responses-arrow" className="comment-replies-arrow"/></button>}
        {isAuthor && <button type="button" className="comment-delete" onClick={() => void onDelete(comment)}><Icon name="trash"/>Eliminar</button>}
      </div>
      {replyingTo === comment.id && <CommentForm currentUser={currentUser} compact placeholder="Escribe una respuesta..." submitLabel="Responder" onSubmit={async (content) => { await onReply(comment.id, content); setReplyingTo(null); }}/>} 
    </div>
  </div>;
}

function containsComment(comments: Comment[], commentId: number | null): boolean {
  if (commentId === null) return false;
  return comments.some((comment) => comment.id === commentId || containsComment(comment.respuestas, commentId));
}

export function CommentItem({ comment, currentUser, replyingTo, setReplyingTo, onReply, onDelete, nested = false }: SharedCommentProps & { comment: Comment; nested?: boolean }) {
  const [responsesOpen, setResponsesOpen] = useState(false);
  const responseCount = comment.cantidad_respuestas;
  const responsesId = `comment-responses-${comment.id}`;

  function toggleResponses() {
    if (responsesOpen && containsComment(comment.respuestas, replyingTo)) {
      setReplyingTo(null);
    }
    setResponsesOpen((open) => !open);
  }

  return <div className={`comment-thread${nested ? " nested" : ""}`}>
    <CommentBody comment={comment} currentUser={currentUser} isReply={nested} replyingTo={replyingTo} setReplyingTo={setReplyingTo} onReply={onReply} onDelete={onDelete} responseCount={responseCount} responsesOpen={responsesOpen} responsesId={responsesId} onToggleResponses={toggleResponses}/>
    {responsesOpen && responseCount > 0 && <div className={nested ? "comment-subresponses" : "comment-replies"} id={responsesId}>{comment.respuestas.map((response) => <CommentItem key={response.id} comment={response} currentUser={currentUser} nested replyingTo={replyingTo} setReplyingTo={setReplyingTo} onReply={onReply} onDelete={onDelete}/>)}</div>}
  </div>;
}
