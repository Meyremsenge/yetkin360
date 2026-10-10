import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup, within, fireEvent } from "@testing-library/react";
import { CertificateStrip } from "./certificate-strip";
import { AboutBlock } from "./about-block";
import type { PublicCertificate } from "@/lib/api/public";

function cert(overrides: Partial<PublicCertificate> = {}): PublicCertificate {
  return {
    kind: "CERTIFICATE",
    title: "Veri Bilimi",
    issuer: null,
    issued_on: "2026-05-01",
    credential_id: "ABC123",
    badge: "COORDINATOR_CONFIRMED",
    provider: "COURSERA",
    verify_url: "https://www.coursera.org/verify/ABC123",
    link_url: null,
    link_host: null,
    ...overrides,
  };
}

const declared = cert({
  title: "Kişisel site",
  kind: "WORK",
  badge: "SELF_DECLARED",
  provider: null,
  verify_url: null,
  issuer: "Kulüp",
  credential_id: null,
  link_url: "https://ornek.dev/proje",
  link_host: "ornek.dev",
});

describe("CertificateStrip", () => {
  afterEach(() => cleanup());

  it("onaylı ve kendi beyanı kayıtları ayrı listelerde gösterir", () => {
    render(<CertificateStrip certificates={[declared, cert()]} />);
    const confirmedList = screen.getByRole("list", { name: /Koordinatör onaylı/ });
    const declaredList = screen.getByRole("list", { name: /Kendi beyanı/ });

    expect(within(confirmedList).getByText("Veri Bilimi")).toBeInTheDocument();
    expect(within(confirmedList).queryByText("Kişisel site")).toBeNull();
    expect(within(declaredList).getByText("Kişisel site")).toBeInTheDocument();
    expect(within(declaredList).getByText("Kişisel site").closest("li")).toHaveClass("border-dashed");
    expect(within(confirmedList).getByText("Veri Bilimi").closest("li")).not.toHaveClass("border-dashed");
  });

  it("onaylı kartta resmi doğrulama linki ve sağlayıcı görünür", () => {
    render(<CertificateStrip certificates={[cert()]} />);
    const link = screen.getByRole("link", { name: /Resmi doğrulama/ });
    expect(link).toHaveAttribute("href", "https://www.coursera.org/verify/ABC123");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("target", "_blank");
    expect(screen.getByText("Coursera")).toBeInTheDocument();
    expect(screen.getByText("ABC123")).toBeInTheDocument();
  });

  it("kendi beyanı linkinde alan adı görünür, nofollow/ugc ve 'doğrulanmamış' notu taşır", () => {
    render(<CertificateStrip certificates={[declared]} />);
    const link = screen.getByRole("link", { name: /ornek\.dev/ });
    expect(link).toHaveAttribute("href", "https://ornek.dev/proje");
    expect(link.getAttribute("rel")).toContain("nofollow");
    expect(link.getAttribute("rel")).toContain("ugc");
    expect(screen.getByText("Doğrulanmamış bağlantı")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Resmi doğrulama/ })).toBeNull();
  });

  it("listeler klavyeyle odaklanabilir", () => {
    render(<CertificateStrip certificates={[cert(), cert({ title: "İkinci" })]} />);
    const list = screen.getByRole("list", { name: /Koordinatör onaylı/ });
    expect(list).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(list, { key: "ArrowRight" });
  });

  it("başlıktaki HTML'i yorumlamaz", () => {
    render(<CertificateStrip certificates={[declared, cert({ title: "<img src=x onerror=alert(1)>" })]} />);
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});

describe("AboutBlock", () => {
  afterEach(() => cleanup());

  it("metni 'Kendi beyanı' etiketiyle ve satır sonlarını koruyarak gösterir", () => {
    render(<AboutBlock about={"Birinci satır\nİkinci satır"} />);
    expect(screen.getByRole("heading", { name: "Hakkımda" })).toBeInTheDocument();
    expect(screen.getByText("Kendi beyanı")).toBeInTheDocument();
    expect(screen.getByText(/Birinci satır/)).toHaveClass("whitespace-pre-line");
    expect(screen.getByText(/doğrulanmış bir kayıt değildir/)).toBeInTheDocument();
  });
});
