import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LoginPlaceholderPage from "@/app/giris/page";
import messages from "@/messages/tr.json";

/**
 * AC-4: LoginPlaceholderPage — ASYNC sunucu bileşeni.
 * neden="oturum-bitti" varsa "Oturumunuz sona erdi" + aria-live.
 * Form YOK (yer tutucu).
 * AC-6: Başlık.
 */

describe("LoginPlaceholderPage (giris/page.tsx)", () => {
  describe("AC-6: Başlık", () => {
    it("AC-6: messages.session.login başlığı vardır", async () => {
      const { container } = render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({}),
        })
      );

      const heading = container.querySelector("h1, h2, h3");
      expect(heading?.textContent).toContain(messages.giris.title);
    });
  });

  describe("AC-4: neden='oturum-bitti' parametresi", () => {
    it("AC-4: neden='oturum-bitti' varsa messages.session.expired gösterilir", async () => {
      render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({ neden: "oturum-bitti" }),
        })
      );

      expect(
        screen.getByText(messages.session.expired)
      ).toBeTruthy();
    });

    it("AC-4: messages.session.expired mesajı aria-live atası içerir", async () => {
      render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({ neden: "oturum-bitti" }),
        })
      );

      const message = screen.getByText(messages.session.expired);
      expect(message.closest("[aria-live]")).not.toBeNull();
    });

    it("AC-4: neden parametresi yoksa messages.session.expired GÖRÜNMEZ", async () => {
      render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({}),
        })
      );

      expect(
        screen.queryByText(messages.session.expired)
      ).toBeNull();
    });

    it("AC-4: neden parametresi undefined ise messages.session.expired GÖRÜNMEZ", async () => {
      render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({ neden: undefined }),
        })
      );

      expect(
        screen.queryByText(messages.session.expired)
      ).toBeNull();
    });

    it("AC-4: neden='oturum-bitti' dışındaki değer GÖRÜNMEZ", async () => {
      render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({
            neden: "başka-neden",
          }),
        })
      );

      expect(
        screen.queryByText(messages.session.expired)
      ).toBeNull();
    });
  });

  describe("AC-6: Form elemanları YOKTUR (yer tutucu)", () => {
    it("AC-6: <form> elemanı YOKTUR", async () => {
      const { container } = render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({}),
        })
      );

      expect(container.querySelector("form")).toBeNull();
    });

    it("AC-6: <input> elemanı YOKTUR", async () => {
      const { container } = render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({}),
        })
      );

      expect(container.querySelector("input")).toBeNull();
    });

    it("AC-6: <button type='submit'> YOKTUR", async () => {
      const { container } = render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({}),
        })
      );

      const submitButton = container.querySelector(
        "button[type='submit']"
      );
      expect(submitButton).toBeNull();
    });
  });

  describe("AC-6: ASYNC sunucu bileşeni", () => {
    it("AC-6: Promise.resolve ile çalışır", async () => {
      const result = await LoginPlaceholderPage({
        searchParams: Promise.resolve({}),
      });

      expect(result).toBeDefined();
    });

    it("AC-6: searchParams Promise'dir", async () => {
      const searchParamsPromise = Promise.resolve({
        neden: "oturum-bitti",
      });

      const result = await LoginPlaceholderPage({
        searchParams: searchParamsPromise,
      });

      expect(result).toBeDefined();
    });
  });

  describe("Davranış Sözleşmesi satır 2: Girişsiz yönlendirme", () => {
    it("Davranış 2: /giris yönlendirmesinin hedefi kırık olmaz", async () => {
      const { container } = render(
        await LoginPlaceholderPage({
          searchParams: Promise.resolve({}),
        })
      );

      // Sayfa render ediliyor ve başlık var → link hedefe gidilebilir
      const heading = container.querySelector("h1, h2, h3");
      expect(heading).not.toBeNull();
    });
  });
});
