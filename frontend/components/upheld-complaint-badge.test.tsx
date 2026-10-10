import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { UpheldComplaintBadge } from "./upheld-complaint-badge";

describe("UpheldComplaintBadge", () => {
  it("renders the count when positive", () => {
    render(<UpheldComplaintBadge count={3} />);
    expect(screen.getByText(/3 doğrulama talebini yanıtsız bıraktı/)).toBeTruthy();
  });
  it.each([0, null, undefined, Number.NaN, -2])("renders nothing for %s", (v) => {
    const { container } = render(<UpheldComplaintBadge count={v as number | null | undefined} />);
    expect(container.innerHTML).toBe("");
  });
});
