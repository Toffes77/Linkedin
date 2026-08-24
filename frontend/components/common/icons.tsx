import type { SVGProps } from "react";

export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: "home" | "network" | "jobs" | "bell" | "search" | "user" | "company" | "business" | "image" | "video" | "write" | "like" | "comment" | "responses-arrow" | "send" | "edit" | "trash" | "more" | "briefcase" | "location" }) {
  const paths: Record<string, React.ReactNode> = {
    home: <><path d="m3 11 9-8 9 8"/><path d="M5 10v11h14V10M9 21v-7h6v7"/></>,
    network: <><circle cx="8" cy="8" r="3"/><circle cx="17" cy="7" r="3"/><path d="M2 20v-2a5 5 0 0 1 10 0v2M13 20v-2a5 5 0 0 1 9-3"/></>,
    jobs: <><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V4h8v3M3 12h18M10 12v2h4v-2"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    company: <><path d="M3 20V6a2 2 0 0 1 2-2h2V2h6v2h2a2 2 0 0 1 2 2v4M3 20h7"/><rect x="6" y="7" width="2" height="2" rx=".4" fill="currentColor" stroke="none"/><rect x="10" y="7" width="2" height="2" rx=".4" fill="currentColor" stroke="none"/><rect x="14" y="7" width="2" height="2" rx=".4" fill="currentColor" stroke="none"/><rect x="6" y="11" width="2" height="2" rx=".4" fill="currentColor" stroke="none"/><rect x="10" y="11" width="2" height="2" rx=".4" fill="currentColor" stroke="none"/><circle cx="17" cy="14" r="3"/><path d="M12 22v-1a5 5 0 0 1 10 0v1"/></>,
    business: <><rect x="4" y="3" width="6" height="18"/><rect x="14" y="8" width="6" height="13"/><path d="M7 7h0M7 11h0M7 15h0M17 12h0M17 16h0"/></>,
    image: <><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 15-5-5L5 20"/></>,
    video: <><rect x="3" y="6" width="13" height="12" rx="2"/><path d="m16 10 5-3v10l-5-3"/></>,
    write: <><path d="M4 4h10M4 9h10M4 14h7M4 19h7M17 13l4 4-5 5h-4v-4z"/></>,
    like: <><path d="M7 10v11H3V10zM7 19c5 2 9 2 11 1 2-1 3-8 2-9-1-1-6 0-6 0s2-5-1-7c-1-1-2 0-2 2l-4 6"/></>,
    comment: <><path d="M21 11.5a8 8 0 0 1-8.5 8 9 9 0 0 1-3.8-.9L3 21l1.6-4.7A8.5 8.5 0 1 1 21 11.5Z"/><path d="M8 10h8M8 14h5"/></>,
    "responses-arrow": <><path d="M2.7 6.2C6.2 3.4 11.4 3.2 15 5.7c2.3 1.6 3.6 4 3.8 6.8h2c.7 0 1 .8.5 1.3l-5.5 5.5a1.1 1.1 0 0 1-1.6 0l-5.5-5.5c-.5-.5-.2-1.3.5-1.3h3.3c-.2-2.2-.8-3.8-2-4.7-1.6-1.2-4-1.4-7.1-.5-.8.2-1.3-.6-.7-1.1Z" fill="currentColor" stroke="none"/><path d="m9.2 18.1 4.6 4.6c.4.4 1 .4 1.4 0l4.6-4.6c.7-.7-.3-1.8-1.1-1.1l-4.2 4.1-4.2-4.1c-.8-.7-1.8.4-1.1 1.1Z" fill="currentColor" stroke="none"/></>,
    send: <path d="m3 3 18 9-18 9 4-9zM7 12h14"/>,
    edit: <><path d="M4 20h4L20 8l-4-4L4 16zM14 6l4 4"/></>,
    trash: <><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/></>,
    more: <><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></>,
    briefcase: <><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V4h8v3"/></>,
    location: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0"/><circle cx="12" cy="10" r="2"/></>,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>;
}
