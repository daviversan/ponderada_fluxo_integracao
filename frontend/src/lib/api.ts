const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = "/api/v1";

export type Currency = "USD" | "BRL";

export interface Product {
  id: string;
  name: string;
  price_cents: number;
  caffeine_mg: number;
  caffeine_currency_ratio: number;
  currency: Currency;
}

export interface ProductCreate {
  name: string;
  price_cents: number;
  caffeine_mg: number;
  currency: Currency;
}

export interface ProductUpdate {
  name?: string;
  price_cents?: number;
  caffeine_mg?: number;
  currency?: Currency;
}

export interface CaffeineLookupResult {
  name: string;
  caffeine_mg: number | null;
  source: string;
}

export interface ApiError {
  detail: string;
  status_code: number;
  request_id: string | null;
}

class ApiClient {
  private base: string;

  constructor(baseUrl: string = API_BASE) {
    this.base = `${baseUrl}${API_PREFIX}`;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.base}${path}`;
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });

    if (!res.ok) {
      const body: ApiError = await res.json().catch(() => ({
        detail: res.statusText,
        status_code: res.status,
        request_id: null,
      }));
      throw body;
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  async createProduct(data: ProductCreate): Promise<Product> {
    return this.request<Product>("/products", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getProduct(id: string): Promise<Product> {
    return this.request<Product>(`/products/${id}`);
  }

  async listProducts(): Promise<Product[]> {
    return this.request<Product[]>("/products");
  }

  async updateProduct(id: string, data: ProductUpdate): Promise<Product> {
    return this.request<Product>(`/products/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteProduct(id: string): Promise<void> {
    return this.request<void>(`/products/${id}`, { method: "DELETE" });
  }

  async searchProducts(query: string): Promise<Product[]> {
    const q = encodeURIComponent(query);
    return this.request<Product[]>(`/products/search?q=${q}`);
  }

  async getRankedProducts(): Promise<Product[]> {
    return this.request<Product[]>("/products/ranked");
  }

  async lookupCaffeine(query: string): Promise<CaffeineLookupResult[]> {
    const q = encodeURIComponent(query);
    return this.request<CaffeineLookupResult[]>(`/products/lookup?q=${q}`);
  }
}

export const api = new ApiClient();
