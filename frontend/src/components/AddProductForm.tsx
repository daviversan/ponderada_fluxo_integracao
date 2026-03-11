"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  Product,
  Currency,
  CaffeineLookupResult,
} from "@/lib/api";

interface AddProductFormProps {
  onProductAdded: (product: Product) => void;
  onCancel: () => void;
}

export default function AddProductForm({
  onProductAdded,
  onCancel,
}: AddProductFormProps) {
  const [name, setName] = useState("");
  const [priceCents, setPriceCents] = useState("");
  const [caffeineMg, setCaffeineMg] = useState("");
  const [currency, setCurrency] = useState<Currency>("USD");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [lookupResults, setLookupResults] = useState<CaffeineLookupResult[]>(
    [],
  );
  const [lookingUp, setLookingUp] = useState(false);
  const [autoFilled, setAutoFilled] = useState(false);
  const lookupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (lookupTimerRef.current) clearTimeout(lookupTimerRef.current);

    const trimmed = name.trim();
    if (trimmed.length < 3) {
      setLookupResults([]);
      return;
    }

    lookupTimerRef.current = setTimeout(async () => {
      setLookingUp(true);
      try {
        const results = await api.lookupCaffeine(trimmed);
        setLookupResults(results);

        const best = results.find((r) => r.caffeine_mg != null);
        if (best?.caffeine_mg != null) {
          setCaffeineMg(String(best.caffeine_mg));
          setAutoFilled(true);
        }
      } catch {
        /* lookup is best-effort; user can type manually */
      } finally {
        setLookingUp(false);
      }
    }, 1000);

    return () => {
      if (lookupTimerRef.current) clearTimeout(lookupTimerRef.current);
    };
  }, [name]);

  const applySuggestion = (result: CaffeineLookupResult) => {
    if (result.caffeine_mg != null) {
      setCaffeineMg(String(result.caffeine_mg));
      setAutoFilled(true);
    }
    if (!name.trim()) {
      setName(result.name);
    }
    setLookupResults([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const cents = Math.round(parseFloat(priceCents) * 100);
    if (isNaN(cents) || cents <= 0) {
      setError("Price must be a positive number.");
      setSubmitting(false);
      return;
    }

    const mg = parseInt(caffeineMg, 10);
    if (isNaN(mg) || mg < 0) {
      setError("Caffeine must be zero or a positive integer.");
      setSubmitting(false);
      return;
    }

    try {
      const product = await api.createProduct({
        name: name.trim(),
        price_cents: cents,
        caffeine_mg: mg,
        currency,
      });
      onProductAdded(product);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "detail" in err
          ? String((err as { detail: string }).detail)
          : "Failed to create product";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          New Product
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
        >
          Cancel
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500 dark:text-zinc-400">
            Product name
          </label>
          <div className="relative">
            <input
              type="text"
              required
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setAutoFilled(false);
              }}
              placeholder="e.g. Red Bull 250ml"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 pr-8 text-sm text-zinc-900 outline-none transition-colors placeholder:text-zinc-400 focus:border-zinc-400 focus:bg-white dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-600 dark:focus:bg-zinc-700"
            />
            {lookingUp && (
              <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-600 dark:border-zinc-700 dark:border-t-zinc-400" />
              </div>
            )}
          </div>
        </div>

        {lookupResults.length > 0 && (
          <div className="space-y-1 rounded-lg border border-blue-100 bg-blue-50 p-3 dark:border-blue-900/40 dark:bg-blue-900/20">
            <p className="text-xs font-medium text-blue-700 dark:text-blue-400">
              Caffeine suggestions (click to apply):
            </p>
            {lookupResults.map((r, i) => (
              <button
                key={i}
                type="button"
                onClick={() => applySuggestion(r)}
                className="block w-full rounded px-2 py-1 text-left text-xs text-blue-800 transition-colors hover:bg-blue-100 dark:text-blue-300 dark:hover:bg-blue-900/40"
              >
                <span className="font-medium">{r.name}</span>
                {r.caffeine_mg != null && (
                  <span className="ml-1 text-blue-600 dark:text-blue-400">
                    — {r.caffeine_mg} mg
                  </span>
                )}
                <span className="ml-1 text-blue-500/70">({r.source})</span>
              </button>
            ))}
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Price
            </label>
            <input
              type="number"
              required
              min="0.01"
              step="0.01"
              value={priceCents}
              onChange={(e) => setPriceCents(e.target.value)}
              placeholder="2.99"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition-colors placeholder:text-zinc-400 focus:border-zinc-400 focus:bg-white dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-600 dark:focus:bg-zinc-700"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Caffeine (mg)
              {autoFilled && (
                <span className="ml-1 text-emerald-600 dark:text-emerald-400">
                  ✓ auto
                </span>
              )}
            </label>
            <input
              type="number"
              required
              min="0"
              step="1"
              value={caffeineMg}
              onChange={(e) => {
                setCaffeineMg(e.target.value);
                setAutoFilled(false);
              }}
              placeholder="80"
              className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors placeholder:text-zinc-400 focus:bg-white dark:focus:bg-zinc-700 dark:placeholder:text-zinc-500 dark:focus:border-zinc-600 ${
                autoFilled
                  ? "border-emerald-300 bg-emerald-50 text-zinc-900 focus:border-emerald-400 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-zinc-100"
                  : "border-zinc-200 bg-zinc-50 text-zinc-900 focus:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
              }`}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-500 dark:text-zinc-400">
              Currency
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value as Currency)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition-colors focus:border-zinc-400 focus:bg-white dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-zinc-600 dark:focus:bg-zinc-700"
            >
              <option value="USD">USD</option>
              <option value="BRL">BRL</option>
            </select>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
      >
        {submitting ? "Creating…" : "Create Product"}
      </button>
    </form>
  );
}
