import { describe, it, expect } from "vitest";
import { MeResponse, isMeResponse } from "@/lib/session/types";

/**
 * AC-7: Type guard validation on /me response.
 * Valid: user object with id string, organizations and institutions arrays, talent_profile optional.
 * Invalid: null, undefined, empty object, missing required fields, wrong types.
 * talent_profile absence is valid (empty durum, not error).
 * organizations[] empty is valid.
 */

describe("isMeResponse", () => {
  describe("Valid responses", () => {
    it("AC-7: minimal valid response (only required fields)", () => {
      const response: unknown = {
        user: { id: "123" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid response with all fields", () => {
      const response: unknown = {
        user: {
          id: "456",
          email: "user@example.com",
          full_name: "Ali Yılmaz",
        },
        talent_profile: { level: "intermediate" },
        organizations: [{ id: "org1", name: "Şirket A" }],
        institutions: [{ id: "inst1" }],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with email but no full_name", () => {
      const response: unknown = {
        user: { id: "789", email: "test@test.com" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with full_name but no email", () => {
      const response: unknown = {
        user: { id: "999", full_name: "Test User" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with talent_profile = null (not error, empty durum)", () => {
      const response: unknown = {
        user: { id: "111" },
        talent_profile: null,
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid without talent_profile field (empty durum)", () => {
      const response: unknown = {
        user: { id: "222" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with talent_profile = empty object", () => {
      const response: unknown = {
        user: { id: "333" },
        talent_profile: {},
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with non-empty organizations", () => {
      const response: unknown = {
        user: { id: "444" },
        organizations: [
          { id: "1", name: "Org A" },
          { id: "2", name: "Org B" },
        ],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with non-empty institutions", () => {
      const response: unknown = {
        user: { id: "555" },
        organizations: [],
        institutions: [{ id: "1", name: "Institute" }],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: valid with extra unknown fields", () => {
      const response: unknown = {
        user: { id: "666", extra: "ignore" },
        organizations: [],
        institutions: [],
        unknownField: "should be ignored",
      };
      expect(isMeResponse(response)).toBe(true);
    });
  });

  describe("Invalid responses", () => {
    it("AC-7: null is invalid", () => {
      expect(isMeResponse(null)).toBe(false);
    });

    it("AC-7: undefined is invalid", () => {
      expect(isMeResponse(undefined)).toBe(false);
    });

    it("AC-7: empty object {} is invalid", () => {
      expect(isMeResponse({})).toBe(false);
    });

    it("AC-7: string is invalid", () => {
      expect(isMeResponse("")).toBe(false);
      expect(isMeResponse("user data")).toBe(false);
    });

    it("AC-7: array [] is invalid", () => {
      expect(isMeResponse([])).toBe(false);
    });

    it("AC-7: number is invalid", () => {
      expect(isMeResponse(123)).toBe(false);
    });

    it("AC-7: missing user field", () => {
      const response: unknown = {
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: user is not an object", () => {
      const response: unknown = {
        user: "string",
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: user is null", () => {
      const response: unknown = {
        user: null,
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: user.id missing", () => {
      const response: unknown = {
        user: { email: "test@test.com" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: user.id is not a string (number)", () => {
      const response: unknown = {
        user: { id: 123 },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: user.id is null", () => {
      const response: unknown = {
        user: { id: null },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: user.id is empty string (still valid — string type)", () => {
      const response: unknown = {
        user: { id: "" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: missing organizations field", () => {
      const response: unknown = {
        user: { id: "123" },
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: organizations is not an array", () => {
      const response: unknown = {
        user: { id: "123" },
        organizations: "string",
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: organizations is null", () => {
      const response: unknown = {
        user: { id: "123" },
        organizations: null,
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: missing institutions field", () => {
      const response: unknown = {
        user: { id: "123" },
        organizations: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: institutions is not an array", () => {
      const response: unknown = {
        user: { id: "123" },
        organizations: [],
        institutions: { id: "1" },
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: institutions is null", () => {
      const response: unknown = {
        user: { id: "123" },
        organizations: [],
        institutions: null,
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: talent_profile is a string (invalid type)", () => {
      const response: unknown = {
        user: { id: "123" },
        talent_profile: "invalid",
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: talent_profile is an array (invalid type)", () => {
      const response: unknown = {
        user: { id: "123" },
        talent_profile: [],
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(false);
    });

    it("AC-7: 204 No Content (empty body)", () => {
      expect(isMeResponse(null)).toBe(false);
    });
  });

  describe("Boş durum (empty durum — valid but minimal)", () => {
    it("AC-7: user with no optional fields, empty organizations, no talent_profile", () => {
      const response: unknown = {
        user: { id: "empty-user" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-7: type-cast as MeResponse for empty durum", () => {
      const emptyResponse: MeResponse = {
        user: { id: "test" },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(emptyResponse)).toBe(true);
    });
  });

  describe("AC-1/AC-2: talent_profile with concrete fields (TypeScript strengthening)", () => {
    it("AC-1: talent_profile with headline field", () => {
      const response: unknown = {
        user: { id: "talent-1" },
        talent_profile: {
          headline: "Software Engineer",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1: talent_profile with headline and department", () => {
      const response: unknown = {
        user: { id: "talent-2" },
        talent_profile: {
          headline: "Senior Developer",
          department: "Engineering",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1: talent_profile with study_year as number", () => {
      const response: unknown = {
        user: { id: "talent-3" },
        talent_profile: {
          study_year: 3,
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1: talent_profile with city field", () => {
      const response: unknown = {
        user: { id: "talent-4" },
        talent_profile: {
          city: "İstanbul",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-S3: talent_profile with visibility enum value PRIVATE", () => {
      const response: unknown = {
        user: { id: "talent-5" },
        talent_profile: {
          visibility: "PRIVATE",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-S3: talent_profile with visibility enum value INSTITUTION", () => {
      const response: unknown = {
        user: { id: "talent-6" },
        talent_profile: {
          visibility: "INSTITUTION",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-S3: talent_profile with visibility enum value ORGANIZATIONS", () => {
      const response: unknown = {
        user: { id: "talent-7" },
        talent_profile: {
          visibility: "ORGANIZATIONS",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-S3: talent_profile with visibility enum value PUBLIC", () => {
      const response: unknown = {
        user: { id: "talent-8" },
        talent_profile: {
          visibility: "PUBLIC",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-S2: talent_profile with public_slug field", () => {
      const response: unknown = {
        user: { id: "talent-9" },
        talent_profile: {
          public_slug: "ali-engineer",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1/AC-2: talent_profile with all concrete fields", () => {
      const response: unknown = {
        user: { id: "talent-full" },
        talent_profile: {
          headline: "Senior Software Engineer",
          department: "Engineering",
          study_year: 4,
          city: "Ankara",
          visibility: "PUBLIC",
          public_slug: "ali-senior-engineer",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1: talent_profile with mixed concrete and unknown fields", () => {
      const response: unknown = {
        user: { id: "talent-mixed" },
        talent_profile: {
          headline: "Developer",
          level: "intermediate",
          some_future_field: "value",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1: talent_profile with null values for optional fields", () => {
      const response: unknown = {
        user: { id: "talent-nulls" },
        talent_profile: {
          headline: null,
          department: null,
          study_year: null,
          city: null,
          visibility: null,
          public_slug: null,
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-1: talent_profile empty object still valid (backward compat with empty durum)", () => {
      const response: unknown = {
        user: { id: "talent-empty" },
        talent_profile: {},
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(response)).toBe(true);
    });

    it("AC-2/AC-S3: TypeScript type guard accepts MeResponse with strengthened talent_profile", () => {
      const strengthenedResponse: MeResponse = {
        user: { id: "talent-ts" },
        talent_profile: {
          headline: "TypeScript Specialist",
          department: "Frontend",
          study_year: 2,
          city: "İzmir",
          visibility: "INSTITUTION",
          public_slug: "ts-specialist",
        },
        organizations: [],
        institutions: [],
      };
      expect(isMeResponse(strengthenedResponse)).toBe(true);
    });
  });
});
