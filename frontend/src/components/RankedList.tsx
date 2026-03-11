"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import ProductCard from "./ProductCard";
import SearchBar from "./SearchBar";
import AddProductForm from "./AddProductForm";

export default function RankedList() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = searchQuery
        ? await api.searchProducts(searchQuery)
        : await api.getRankedProducts();
      setProducts(data);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "detail" in err
          ? String((err as { detail: string }).detail)
          : "Failed to load products";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteProduct(id);
      setProducts((prev) => prev.filter((p) => p.id !== id));
    } catch {
      setError("Failed to delete product");
    }
  };

  const handleProductAdded = (product: Product) => {
    setProducts((prev) =>
      [...prev, product].sort(
        (a, b) => b.caffeine_currency_ratio - a.caffeine_currency_ratio,
      ),
    );
    setShowAddForm(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <SearchBar onSearch={handleSearch} />
        </div>
        <button
          onClick={() => setShowAddForm((prev) => !prev)}
          className="shrink-0 rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-medium text-zinc-700 shadow-sm transition-colors hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          {showAddForm ? "Cancel" : "+ Add Product"}
        </button>
      </div>

      {showAddForm && (
        <AddProductForm
          onProductAdded={handleProductAdded}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-600 dark:border-zinc-700 dark:border-t-zinc-400" />
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-400">
          {error}
          <button
            onClick={fetchProducts}
            className="ml-2 font-medium underline underline-offset-2 hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && products.length === 0 && (
        <div className="rounded-xl border border-zinc-200 bg-white px-4 py-12 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <p className="text-zinc-500 dark:text-zinc-400">
            {searchQuery
              ? `No products found for "${searchQuery}"`
              : "No products yet. Add one to get started!"}
          </p>
        </div>
      )}

      {!loading && !error && products.length > 0 && (
        <div className="space-y-3">
          {products.map((product, idx) => (
            <ProductCard
              key={product.id}
              product={product}
              rank={searchQuery ? undefined : idx + 1}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
