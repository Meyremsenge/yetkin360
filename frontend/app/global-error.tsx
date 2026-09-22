"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <>
      {/* AC-6: DOCTYPE */}
      {"<!doctype html>"}
      <html lang="tr">
        <body style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "100vh",
              margin: 0,
              padding: "1rem",
            }}
          >
            <div style={{ maxWidth: "500px", textAlign: "center" }}>
              <h1 style={{ fontSize: "2rem", marginBottom: "1rem", color: "#111827" }}>
                Bir hata oluştu
              </h1>
              <p
                style={{
                  marginBottom: "1.5rem",
                  color: "#4b5563",
                  fontSize: "1rem",
                }}
              >
                Uygulama şu anda kullanılamıyor. Lütfen sayfayı yenileyin.
              </p>
              <button
                onClick={reset}
                style={{
                  padding: "0.5rem 1rem",
                  backgroundColor: "#1e293b",
                  color: "white",
                  border: "none",
                  borderRadius: "0.375rem",
                  fontSize: "1rem",
                  fontWeight: "500",
                  cursor: "pointer",
                }}
              >
                Yeniden dene
              </button>
            </div>
          </div>
        </body>
      </html>
    </>
  );
}
