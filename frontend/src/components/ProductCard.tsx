"use client";

import { Product } from "@/lib/api";

interface ProductCardProps {
  product: Product;
  rank?: number;
  onDelete?: (id: string) => void;
}

const currencySymbol: Record<string, string> = {
  USD: "$",
  BRL: "R$",
};

export default function ProductCard({
  product,
  rank,
  onDelete,
}: ProductCardProps) {
  const priceDisplay = (product.price_cents / 100).toFixed(2);
  const symbol = currencySymbol[product.currency] ?? product.currency;

  return (
    <div className="group relative flex items-start gap-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900">
      {rank != null && (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
          {rank}
        </div>
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {product.name}
          </h3>
          <span className="shrink-0 rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
            {product.currency}
          </span>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-zinc-500 dark:text-zinc-400">
          <span>
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {symbol}
              {priceDisplay}
            </span>
          </span>
          <span>
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {product.caffeine_mg}
            </span>{" "}
            mg caffeine
          </span>
        </div>

        <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1 text-sm font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
            />
          </svg>
          {product.caffeine_currency_ratio.toFixed(2)} mg/{symbol}
        </div>
      </div>

      {onDelete && (
        <button
          onClick={() => onDelete(product.id)}
          className="shrink-0 rounded-lg p-1.5 text-zinc-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100 dark:hover:bg-red-900/30 dark:hover:text-red-400"
          aria-label={`Delete ${product.name}`}
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
