import Image from "next/image";
import { mediaUrl } from "@/lib/api";

export function CompanyLogo({
  name,
  src,
  className,
}: {
  name: string;
  src?: string | null;
  className: string;
}) {
  const logo = mediaUrl(src);
  return <span className={className}>
    {logo ? <Image unoptimized src={logo} alt={`Logo de ${name}`} width={112} height={112} className="company-logo-image"/> : name.trim().slice(0, 1).toUpperCase()}
  </span>;
}
