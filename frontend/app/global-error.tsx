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
        <body
          style={{
            margin: 0,
            backgroundColor: "#FAF8F5",
            color: "#221F1B",
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "center",
              paddingTop: "6rem",
              minHeight: "100vh",
              margin: 0,
              padding: "1rem",
            }}
          >
            <div style={{ maxWidth: "560px", width: "100%", textAlign: "left" }}>
              <h1 style={{ fontFamily: "Georgia, serif", fontWeight: 600, fontSize: "2rem", marginBottom: "0.5rem", color: "#221F1B" }}>
                Bir hata oluştu
              </h1>
              <p
                style={{
                  marginBottom: "1.5rem",
                  color: "#625C55",
                  fontSize: "1rem",
                }}
              >
                Uygulama şu anda kullanılamıyor. Lütfen sayfayı yenileyin.
              </p>
              <button
                onClick={reset}
                style={{
                  height: "2.5rem",
                  padding: "0 1rem",
                  backgroundColor: "#265445",
                  color: "#FAF8F5",
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
