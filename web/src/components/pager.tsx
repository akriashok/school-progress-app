import { t } from "@/i18n";
import { Button } from "@/components/ui/button";

export function Pager({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-3 p-3 text-sm">
      <span className="text-muted-foreground">{t("common.pageOf", { page, pages })}</span>
      <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        {t("common.previous")}
      </Button>
      <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        {t("common.next")}
      </Button>
    </div>
  );
}
