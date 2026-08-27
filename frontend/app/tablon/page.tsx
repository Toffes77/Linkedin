import { BoardPage } from "@/components/board/board-page";

export default async function TablonPage({
  searchParams,
}: {
  searchParams: Promise<{ vista?: string; promocion?: string }>;
}) {
  const params = await searchParams;
  const highlightedPromotion = Number(params.promocion);
  return (
    <BoardPage
      initialView={params.vista === "mias" ? "mine" : "public"}
      highlightedPromotion={Number.isInteger(highlightedPromotion) ? highlightedPromotion : null}
    />
  );
}
