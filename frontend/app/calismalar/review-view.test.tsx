import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, within } from "@testing-library/react";
import { ReviewView } from "@/app/calismalar/review-view";
import type { EngagementSummary } from "@/lib/api/engagements";
import type { ReviewerScope } from "@/lib/ui/engagement-review";

function summary(overrides: Partial<EngagementSummary>): EngagementSummary {
  return {
    id: "eng-1",
    title: "Frontend Stajı",
    kind: "INTERNSHIP",
    status: "ACTIVE",
    organization_id: "org-1",
    institution_id: null,
    organization_name: "Acme A.Ş.",
    version: 1,
    updated_at: "2026-09-01T00:00:00Z",
    talent_id: "talent-1",
    talent_name: "Ayşe Yılmaz",
    ...overrides,
  };
}

const ORG: ReviewerScope = { organizationIds: new Set(["org-1"]), institutionIds: new Set() };

const ITEMS = [
  summary({ id: "eng-wait", title: "Veri Analizi", status: "PENDING_EVALUATION", talent_name: "Can Demir" }),
  summary({ id: "eng-active", title: "Frontend Stajı", status: "ACTIVE" }),
  summary({ id: "eng-verified", title: "Mobil Proje", status: "VERIFIED", talent_name: "İpek Şahin" }),
  summary({ id: "eng-cancelled", title: "Yarım Kalan", status: "CANCELLED", talent_name: "Mert Kaya" }),
  summary({ id: "eng-draft", title: "Taslak Çalışma", status: "DRAFT", talent_name: "Gizli Öğrenci" }),
];

describe("ReviewView (kurum/kuruluş çalışma listesi)", () => {
  afterEach(() => {
    cleanup();
  });

  it("sayaçlar bekleyen, onaylanan ve doğrulanmış çalışma sayısını gösterir", () => {
    render(<ReviewView items={ITEMS} scope={ORG} />);

    expect(screen.getByTestId("review-count-awaiting").textContent).toBe("1");
    expect(screen.getByTestId("review-count-approved").textContent).toBe("3");
    expect(screen.getByTestId("review-count-verified").textContent).toBe("1");
  });

  it("değerlendirme bekleyen çalışma, forma götüren adlandırılmış bağlantıyla listelenir", () => {
    render(<ReviewView items={ITEMS} scope={ORG} />);

    const row = screen.getByTestId("review-awaiting-row");
    expect(within(row).getByText("Can Demir")).toBeTruthy();
    expect(within(row).getByText("Değerlendirmenizi bekliyor")).toBeTruthy();
    const link = within(row).getByRole("link", { name: "Can Demir, Veri Analizi: Değerlendir" });
    expect(link.getAttribute("href")).toBe("/calismalar/eng-wait/degerlendirme");
  });

  it("öğrencinin göndermediği taslak hiçbir yerde görünmez", () => {
    render(<ReviewView items={ITEMS} scope={ORG} />);

    expect(screen.queryByText("Taslak Çalışma")).toBeNull();
    expect(screen.queryByText("Gizli Öğrenci")).toBeNull();
  });

  it("sekme, onaylanan çalışmaları duruma göre süzer", () => {
    render(<ReviewView items={ITEMS} scope={ORG} />);
    expect(screen.getAllByTestId("review-approved-card")).toHaveLength(3);

    fireEvent.click(screen.getByRole("tab", { name: /Doğrulanmış/ }));

    const cards = screen.getAllByTestId("review-approved-card");
    expect(cards).toHaveLength(1);
    expect(within(cards[0]).getByText("İpek Şahin")).toBeTruthy();
    expect(within(cards[0]).getByTestId("calismalar-verified-mark")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: /Kapanmış/ }));
    expect(within(screen.getByTestId("review-approved-card")).getByText("Mert Kaya")).toBeTruthy();
  });

  it("arama öğrenci adına ve başlığa göre süzer; sonuç yoksa bunu söyler", () => {
    render(<ReviewView items={ITEMS} scope={ORG} />);
    const search = screen.getByLabelText("Öğrenci ya da çalışma ara");

    fireEvent.change(search, { target: { value: "ipek" } });
    expect(within(screen.getByTestId("review-approved-card")).getByText("Mobil Proje")).toBeTruthy();

    fireEvent.change(search, { target: { value: "frontend" } });
    expect(within(screen.getByTestId("review-approved-card")).getByText("Ayşe Yılmaz")).toBeTruthy();

    fireEvent.change(search, { target: { value: "olmayan" } });
    expect(screen.queryByTestId("review-approved-card")).toBeNull();
    expect(screen.getByText("Aramanızla eşleşen çalışma yok.")).toBeTruthy();
  });

  it("bekleyen yoksa bölüm boş durumunu gösterir", () => {
    render(<ReviewView items={[summary({})]} scope={ORG} />);

    expect(screen.getByText("Şu an sizden beklenen bir işlem yok.")).toBeTruthy();
    expect(screen.queryByTestId("review-awaiting-row")).toBeNull();
  });

  it("adı boş gelen öğrenci için yer tutucu gösterilir", () => {
    render(<ReviewView items={[summary({ talent_name: "" })]} scope={ORG} />);

    expect(within(screen.getByTestId("review-approved-card")).getByText("Adsız öğrenci")).toBeTruthy();
  });
});
