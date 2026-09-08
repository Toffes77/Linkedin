import type { ReactNode } from "react";
import { readFileSync } from "node:fs";
import path from "node:path";
import Image from "next/image";
import Link from "next/link";

export const metadata = {
  title: "Términos y Condiciones | Atanes",
  description: "Términos y Condiciones de uso de Atanes.",
};

function renderInline(value: string): ReactNode[] {
  return value.split(/(`[^`]+`|\[[^\]]+\]\([^\s)]+\))/g).map((part, index) => {
    const code = /^`([^`]+)`$/.exec(part);
    if (code) return <code key={`code-${index}`}>{code[1]}</code>;

    const link = /^\[([^\]]+)\]\(([^\s)]+)\)$/.exec(part);
    if (link) {
      const [label, href] = [link[1], link[2]];
      return href.startsWith("/")
        ? <Link key={`link-${index}`} href={href}>{label}</Link>
        : <a key={`link-${index}`} href={href}>{label}</a>;
    }

    return part;
  });
}

function renderMarkdown(markdown: string): ReactNode[] {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];
  let listOrdered = false;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(<p key={`paragraph-${blocks.length}`}>{renderInline(paragraph.join(" "))}</p>);
    paragraph = [];
  };

  const flushList = () => {
    if (!list.length) return;
    const List = listOrdered ? "ol" : "ul";
    blocks.push(
      <List key={`list-${blocks.length}`}>
        {list.map((item, index) => <li key={`${index}-${item}`}>{renderInline(item)}</li>)}
      </List>,
    );
    list = [];
    listOrdered = false;
  };

  lines.forEach((line) => {
    const heading = /^(#{1,3})\s+(.+)$/.exec(line.trim());
    const unordered = /^[-*]\s+(.+)$/.exec(line.trim());
    const ordered = /^\d+\.\s+(.+)$/.exec(line.trim());

    if (!line.trim()) {
      flushParagraph();
      flushList();
      return;
    }
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      const Heading = `h${level}` as "h1" | "h2" | "h3";
      blocks.push(<Heading key={`heading-${blocks.length}`}>{heading[2]}</Heading>);
      return;
    }
    if (unordered || ordered) {
      flushParagraph();
      const nextOrdered = Boolean(ordered);
      if (list.length && listOrdered !== nextOrdered) flushList();
      listOrdered = nextOrdered;
      list.push((unordered ?? ordered)![1]);
      return;
    }
    flushList();
    paragraph.push(line.trim());
  });

  flushParagraph();
  flushList();
  return blocks;
}

export default function TermsPage() {
  const termsPath = path.join(process.cwd(), "content", "terminos.md");
  const markdown = readFileSync(termsPath, "utf8");

  return (
    <main className="legal-page">
      <header className="auth-header legal-header">
        <Link href="/login" aria-label="Atanes">
          <Image src="/assets/atanes_logo.svg" alt="Atanes" width={2037} height={772} className="wordmark" priority />
        </Link>
        <nav>
          <Link href="/login" className="join-link">Volver a iniciar sesión</Link>
        </nav>
      </header>
      <article className="card legal-document">
        {renderMarkdown(markdown)}
        <footer className="legal-document-footer">
          <Link href="/registro" className="primary-button">Crear una cuenta</Link>
        </footer>
      </article>
    </main>
  );
}
