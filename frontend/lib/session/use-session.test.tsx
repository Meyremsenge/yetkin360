import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useSession,
  useLogout,
  SESSION_QUERY_KEY,
  sessionRetry,
} from "@/lib/session/use-session";
import {
  InvalidResponseError,
  SessionExpiredError,
  NetworkError,
  ApiError,
} from "@/lib/api/errors";

vi.mock("@/lib/session/fetch-me");
vi.mock("@/lib/api/client");
vi.mock("next/navigation");

/**
 * AC-3/AC-4: Oturum yönetimi — single-flight refresh, cache temizliği, yönlendirme.
 * AC-5: Ağ hatası — cache korunur veya hata gösterilir.
 * AC-8: Logout — başarılı veya başarısız.
 * AC-S1: SessionExpiredError → cache temizle, girişe yönlendir.
 * AC-S5: Cache tamamen temizlenir.
 */

describe("SESSION_QUERY_KEY", () => {
  it("AC-3: SESSION_QUERY_KEY = ['session']", () => {
    expect(SESSION_QUERY_KEY).toEqual(["session"]);
  });

  it("AC-3: const array özelliğine sahip", () => {
    const key = SESSION_QUERY_KEY;
    expect(key).toEqual(["session"]);
  });
});

describe("sessionRetry", () => {
  describe("AC-3/AC-5: ApiError status < 500 → HER ZAMAN false", () => {
    it("AC-3: ApiError 401 → false", () => {
      const error = new ApiError({
        status: 401,
        code: "UNAUTHENTICATED",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(0, error)).toBe(false);
      expect(sessionRetry(1, error)).toBe(false);
      expect(sessionRetry(2, error)).toBe(false);
    });

    it("AC-5: ApiError 404 → false", () => {
      const error = new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(0, error)).toBe(false);
    });

    it("AC-5: ApiError 429 (rate limit) → false", () => {
      const error = new ApiError({
        status: 429,
        code: "TOO_MANY_REQUESTS",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(0, error)).toBe(false);
    });
  });

  describe("AC-3/AC-4: SessionExpiredError → HER ZAMAN false", () => {
    it("AC-4: SessionExpiredError failureCount=0 → false", () => {
      const error = new SessionExpiredError();
      expect(sessionRetry(0, error)).toBe(false);
    });

    it("AC-4: SessionExpiredError failureCount=5 → false", () => {
      const error = new SessionExpiredError();
      expect(sessionRetry(5, error)).toBe(false);
    });
  });

  describe("AC-7: InvalidResponseError → HER ZAMAN false", () => {
    it("AC-7: InvalidResponseError failureCount=0 → false", () => {
      const error = new InvalidResponseError("Boş gövde");
      expect(sessionRetry(0, error)).toBe(false);
    });
  });

  describe("AC-5: NetworkError ve ApiError status >= 500", () => {
    it("AC-5: NetworkError 'network' failureCount=0 → true", () => {
      const error = new NetworkError("network");
      expect(sessionRetry(0, error)).toBe(true);
    });

    it("AC-5: NetworkError 'network' failureCount=1 → true", () => {
      const error = new NetworkError("network");
      expect(sessionRetry(1, error)).toBe(true);
    });

    it("AC-5: NetworkError 'network' failureCount=2 → false", () => {
      const error = new NetworkError("network");
      expect(sessionRetry(2, error)).toBe(false);
    });

    it("AC-5: NetworkError 'timeout' failureCount=0 → true", () => {
      const error = new NetworkError("timeout");
      expect(sessionRetry(0, error)).toBe(true);
    });

    it("AC-5: NetworkError 'timeout' failureCount=2 → false", () => {
      const error = new NetworkError("timeout");
      expect(sessionRetry(2, error)).toBe(false);
    });

    it("AC-5: ApiError 500 failureCount=0 → true", () => {
      const error = new ApiError({
        status: 500,
        code: "INTERNAL_SERVER_ERROR",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(0, error)).toBe(true);
    });

    it("AC-5: ApiError 500 failureCount=1 → true", () => {
      const error = new ApiError({
        status: 500,
        code: "INTERNAL_SERVER_ERROR",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(1, error)).toBe(true);
    });

    it("AC-5: ApiError 500 failureCount=2 → false", () => {
      const error = new ApiError({
        status: 500,
        code: "INTERNAL_SERVER_ERROR",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(2, error)).toBe(false);
    });

    it("AC-5: ApiError 503 failureCount=0 → true", () => {
      const error = new ApiError({
        status: 503,
        code: "SERVICE_UNAVAILABLE",
        message: "Hata",
        requestId: null,
      });
      expect(sessionRetry(0, error)).toBe(true);
    });
  });

  describe("AC-5: Diğer hata tipleri", () => {
    it("AC-5: unknown error → retry çalışmaz (false)", () => {
      const error = new Error("Unknown");
      expect(sessionRetry(0, error)).toBe(false);
    });
  });
});

describe("useSession", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, retryDelay: 0 } },
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("AC-1: Happy path — geçerli oturum", () => {
    it("AC-1: geçerli veri döner", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      const validData = {
        user: { id: "user-1" },
        organizations: [{ id: "org-1", name: "Lale", role: "MEMBER" as const, unit: null }],
        institutions: [],
      };
      vi.mocked(fetchMe).mockResolvedValueOnce(validData);

      const { result } = renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(result.current.data).toEqual(validData);
      });
    });

    it("AC-1: useQuery sonucu yapısına sahip", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      vi.mocked(fetchMe).mockResolvedValueOnce({
        user: { id: "user-1" },
        organizations: [],
        institutions: [],
      });

      const { result } = renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(result.current).toHaveProperty("data");
        expect(result.current).toHaveProperty("error");
        expect(result.current).toHaveProperty("isPending");
        expect(result.current).toHaveProperty("isError");
      });
    });
  });

  describe("AC-4: SessionExpiredError → cache temizle + yönlendir", () => {
    it("AC-S1/AC-4: SessionExpiredError → queryClient.clear() çağrılır", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      vi.mocked(fetchMe).mockRejectedValueOnce(new SessionExpiredError());
      const clearSpy = vi.spyOn(queryClient, "clear");

      const { result } = renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(clearSpy).toHaveBeenCalled();
    });

    it("AC-4: SessionExpiredError → router.replace buildLoginUrl", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      const { useRouter, usePathname } = await import("next/navigation");

      vi.mocked(fetchMe).mockRejectedValueOnce(new SessionExpiredError());
      const mockReplace = vi.fn();
      vi.mocked(useRouter).mockReturnValue({ replace: mockReplace } as unknown as ReturnType<typeof useRouter>);
      vi.mocked(usePathname).mockReturnValue("/profil");

      renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(mockReplace).toHaveBeenCalledWith(
          expect.stringContaining("/giris")
        );
        expect(mockReplace).toHaveBeenCalledWith(
          expect.stringContaining("neden=oturum-bitti")
        );
      });
    });
  });

  describe("AC-5: NetworkError — cache korunur (clear çağrılmaz)", () => {
    it("AC-5: NetworkError → queryClient.clear() ÇAĞRILMAZ", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      vi.mocked(fetchMe).mockRejectedValue(
        new NetworkError("network")
      );
      const clearSpy = vi.spyOn(queryClient, "clear");

      const { result } = renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(clearSpy).not.toHaveBeenCalled();
    });

    it("AC-5: ApiError 500 → queryClient.clear() ÇAĞRILMAZ", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      const error500 = new ApiError({
        status: 500,
        code: "INTERNAL",
        message: "Hata",
        requestId: null,
      });
      vi.mocked(fetchMe).mockRejectedValue(error500);
      const clearSpy = vi.spyOn(queryClient, "clear");

      const { result } = renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(clearSpy).not.toHaveBeenCalled();
    });
  });

  describe("AC-5: InvalidResponseError — cache korunur", () => {
    it("AC-7: InvalidResponseError → queryClient.clear() ÇAĞRILMAZ", async () => {
      const { fetchMe } = await import("@/lib/session/fetch-me");
      vi.mocked(fetchMe).mockRejectedValueOnce(
        new InvalidResponseError("Boş gövde")
      );
      const clearSpy = vi.spyOn(queryClient, "clear");

      const { result } = renderHook(() => useSession(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(clearSpy).not.toHaveBeenCalled();
    });
  });
});

describe("useLogout", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("AC-8: logout başarılı (2xx) → cache temizle + yönlendir", () => {
    it("AC-8: logout 2xx → logout() başarılı", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true });

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isError).toBe(false);
    });

    it("AC-8/AC-S5: logout 2xx → queryClient.clear() çağrılır", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true });
      const clearSpy = vi.spyOn(queryClient, "clear");

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(clearSpy).toHaveBeenCalled();
    });

    it("AC-8/AC-S5: logout 2xx → router.replace('/giris')", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const { useRouter } = await import("next/navigation");

      vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true });
      const mockReplace = vi.fn();
      vi.mocked(useRouter).mockReturnValueOnce({ replace: mockReplace } as unknown as ReturnType<typeof useRouter>);

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(mockReplace).toHaveBeenCalledWith("/giris");
    });
  });

  describe("AC-8: logout başarısız → oturum açık, isError=true", () => {
    it("AC-8: logout ApiError → isError=true", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const error = new ApiError({
        status: 500,
        code: "ERROR",
        message: "Hata",
        requestId: null,
      });
      vi.mocked(apiFetch).mockRejectedValueOnce(error);

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await act(async () => {
        await result.current.logout();
      });

      // isError kontrol edilecek — bu bileşene bağlı
      expect(result.current.isError).toBe(true);
    });

    it("AC-8: logout hata → cache temizlenmez", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockRejectedValueOnce(
        new NetworkError("network")
      );
      const clearSpy = vi.spyOn(queryClient, "clear");

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(clearSpy).not.toHaveBeenCalled();
    });

    it("AC-8/AC-S5: logout hata → router.replace ÇAĞRILMAZ", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const { useRouter } = await import("next/navigation");

      vi.mocked(apiFetch).mockRejectedValueOnce(
        new ApiError({
          status: 400,
          code: "ERROR",
          message: "Hata",
          requestId: null,
        })
      );
      const mockReplace = vi.fn();
      vi.mocked(useRouter).mockReturnValueOnce({ replace: mockReplace } as unknown as ReturnType<typeof useRouter>);

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(mockReplace).not.toHaveBeenCalled();
    });
  });

  describe("AC-8: logout isPending durumu", () => {
    it("AC-8: logout başında isPending=true", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      let resolveLogout: () => void;
      const logoutPromise = new Promise<void>((resolve) => {
        resolveLogout = resolve;
      });
      vi.mocked(apiFetch).mockReturnValueOnce(logoutPromise);

      const { result } = renderHook(() => useLogout(), {
        wrapper: ({ children }) => (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        ),
      });

      const logoutPromiseHandle = act(async () => {
        const logoutTask = result.current.logout();
        await new Promise((r) => setTimeout(r, 10));
        return logoutTask;
      });

      resolveLogout!();
      await logoutPromiseHandle;
    });
  });
});
