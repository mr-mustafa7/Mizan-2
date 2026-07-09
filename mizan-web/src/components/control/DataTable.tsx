"use client";

import { useMemo, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  searchValue?: (row: T) => string;
}

interface DataTableProps<T> {
  rows: T[];
  columns: DataTableColumn<T>[];
  searchPlaceholder?: string;
  emptyMessage?: string;
  pageSize?: number;
  rowKey: (row: T) => string;
}

export function DataTable<T>({
  rows,
  columns,
  searchPlaceholder = "Search",
  emptyMessage = "No rows to display.",
  pageSize = 10,
  rowKey,
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      columns.some((col) =>
        (col.searchValue?.(row) ?? String(col.render(row)))
          .toLowerCase()
          .includes(q)
      )
    );
  }, [rows, columns, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageRows = filtered.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div className="overflow-hidden rounded-xl border border-[#1e2d4a] bg-[#0f1729]">
      <div className="flex flex-col gap-3 border-b border-[#1e2d4a] px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
        <input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
          placeholder={searchPlaceholder}
          className="w-full rounded-lg border border-[#243552] bg-[#0b1220] px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none sm:max-w-xs"
        />
        <button
          type="button"
          className="hidden rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white sm:block"
        >
          Search
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[720px] w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e2d4a] bg-[#0b1220] text-left text-xs uppercase tracking-wide text-slate-500">
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 font-medium">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-slate-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              pageRows.map((row) => (
                <tr
                  key={rowKey(row)}
                  className="border-b border-[#1e2d4a]/60 hover:bg-[#131f35]"
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className="px-4 py-3 text-slate-300 whitespace-nowrap"
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#1e2d4a] px-4 py-3 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className={cn(
              "rounded border border-[#243552] px-2 py-1",
              currentPage <= 1
                ? "cursor-not-allowed opacity-40"
                : "hover:bg-[#131f35]"
            )}
          >
            Prev
          </button>
          <span>
            Page {currentPage} of {totalPages} ({filtered.length} rows)
          </span>
          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className={cn(
              "rounded border border-[#243552] px-2 py-1",
              currentPage >= totalPages
                ? "cursor-not-allowed opacity-40"
                : "hover:bg-[#131f35]"
            )}
          >
            Next
          </button>
        </div>
        <span>Rows: {pageSize}</span>
      </div>
    </div>
  );
}
