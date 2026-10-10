import { describe, it, expect, vi, beforeEach } from "vitest";
import * as client from "./client";
import * as evidence from "./evidence";
import {
  createComplaint,
  listComplaints,
  getComplaint,
  submitExplanation,
  uploadAttachment,
  getAttachmentDownloadUrl,
  adminListComplaints,
  adminGetComplaint,
  adminTransition,
} from "./complaints";
import { ApiError } from "./errors";

vi.mock("./client");
vi.mock("./evidence", () => ({ uploadFileToStorage: vi.fn() }));
const mockApiFetch = vi.mocked(client.apiFetch);
const mockStorageUpload = vi.mocked(evidence.uploadFileToStorage);

const OWNER_WIRE = {
  id: "c-owner",
  viewer_role: "OWNER",
  subject_type: "ENGAGEMENT",
  subject_id: "e1",
  status_label: "IN_PROGRESS",
  description: "Yanıt yok",
  resolution_reason: null,
  created_at: "2026-10-01T10:00:00Z",
  closed_at: null,
  attachments: [{ id: "f1", mime_type: "application/pdf", size_bytes: 10, created_at: "2026-10-01T10:01:00Z" }],
};

const RESPONDENT_WIRE = {
  id: "c-resp",
  viewer_role: "RESPONDENT",
  subject_type: "ENGAGEMENT",
  subject_id: "e2",
  status: "EXPLANATION_REQUESTED",
  request_note: "Lütfen gerekçe yazın",
  explanation_due_at: "2026-10-08T10:00:00Z",
  explanation_text: null,
  created_at: "2026-10-05T10:00:00Z",
};

describe("lib/api/complaints", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiFetch.mockReset();
  });

  it("createComplaint posts only subject_type, subject_id, description", async () => {
    mockApiFetch.mockResolvedValueOnce({
      id: "c1",
      status: "OPEN",
      status_label: "IN_PROGRESS",
      subject_type: "ENGAGEMENT",
      subject_id: "e1",
    });
    const created = await createComplaint({ subject_type: "ENGAGEMENT", subject_id: "e1", description: "Yanıt yok" });
    expect(mockApiFetch).toHaveBeenCalledWith("/complaints", {
      method: "POST",
      body: { subject_type: "ENGAGEMENT", subject_id: "e1", description: "Yanıt yok" },
    });
    expect(created.status_label).toBe("IN_PROGRESS");
  });

  it("createComplaint propagates 409 TOO_EARLY as ApiError", async () => {
    mockApiFetch.mockRejectedValueOnce(
      new ApiError({ status: 409, code: "TOO_EARLY", message: "x", requestId: null }),
    );
    await expect(
      createComplaint({ subject_type: "ENGAGEMENT", subject_id: "e1", description: "yeterince uzun" }),
    ).rejects.toMatchObject({ status: 409, code: "TOO_EARLY" });
  });

  it("createComplaint throws when the body is empty", async () => {
    mockApiFetch.mockResolvedValueOnce(undefined);
    await expect(
      createComplaint({ subject_type: "ENGAGEMENT", subject_id: "e1", description: "yeterince uzun" }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("listComplaints merges own and assigned complaints, newest first, and normalises both views", async () => {
    mockApiFetch.mockImplementation(async (path: string) => {
      if (path.startsWith("/complaints/assigned")) {
        return { items: [RESPONDENT_WIRE], limit: 200, offset: 0, has_more: false };
      }
      return { items: [OWNER_WIRE], limit: 200, offset: 0, has_more: false };
    });
    const items = await listComplaints();

    expect(items.map((c) => c.id)).toEqual(["c-resp", "c-owner"]);
    const respondent = items[0];
    expect(respondent.viewer_role).toBe("RESPONDENT");
    expect(respondent.status).toBe("EXPLANATION_REQUESTED");
    // The respondent wire view has no status_label: it is derived (intermediate → IN_PROGRESS).
    expect(respondent.status_label).toBe("IN_PROGRESS");
    expect(respondent.admin_note).toBe("Lütfen gerekçe yazın");
    expect(items[1].viewer_role).toBe("OWNER");
    expect(items[1].attachments).toEqual([{ id: "f1", mime_type: "application/pdf", size_bytes: 10 }]);
  });

  it("listComplaints follows has_more so a long list is not truncated", async () => {
    mockApiFetch.mockImplementation(async (path: string) => {
      if (path.startsWith("/complaints/assigned")) return { items: [], has_more: false };
      if (path.includes("offset=0")) return { items: [{ ...OWNER_WIRE, id: "a" }], has_more: true };
      if (path.includes("offset=200")) return { items: [{ ...OWNER_WIRE, id: "b" }], has_more: false };
      throw new Error(`unexpected path ${path}`);
    });
    const items = await listComplaints();
    expect(items.map((c) => c.id).sort()).toEqual(["a", "b"]);
  });

  it("listComplaints treats a terminal respondent status as its own label", async () => {
    mockApiFetch.mockImplementation(async (path: string) =>
      path.startsWith("/complaints/assigned")
        ? { items: [{ ...RESPONDENT_WIRE, status: "UPHELD" }], has_more: false }
        : { items: [], has_more: false },
    );
    const [item] = await listComplaints();
    expect(item.status_label).toBe("UPHELD");
  });

  it("listComplaints tolerates a missing items field", async () => {
    mockApiFetch.mockResolvedValue({});
    expect(await listComplaints()).toEqual([]);
  });

  it("getComplaint encodes the id and maps resolution_reason", async () => {
    mockApiFetch.mockResolvedValueOnce({ ...OWNER_WIRE, status_label: "DISMISSED", resolution_reason: "Haksız" });
    const complaint = await getComplaint("a/b");
    expect(mockApiFetch).toHaveBeenCalledWith("/complaints/a%2Fb");
    expect(complaint.result_reason).toBe("Haksız");
  });

  it("submitExplanation posts {text}", async () => {
    mockApiFetch.mockResolvedValueOnce(RESPONDENT_WIRE);
    await submitExplanation("c1", "Geç kaldık");
    expect(mockApiFetch).toHaveBeenCalledWith("/complaints/c1/explanation", {
      method: "POST",
      body: { text: "Geç kaldık" },
    });
  });

  it("adminListComplaints sends limit/offset and normalises the page", async () => {
    mockApiFetch.mockResolvedValueOnce({
      items: [
        {
          id: "c1",
          status: "OPEN",
          subject_type: "ENGAGEMENT",
          subject_id: "e1",
          subject_pending: false,
          target_name: "Örnek Üniversitesi",
          created_at: "2026-10-01T10:00:00Z",
        },
      ],
      limit: 50,
      offset: 50,
      has_more: true,
    });
    const page = await adminListComplaints({ limit: 50, offset: 50 });
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/complaints?limit=50&offset=50");
    expect(page.has_more).toBe(true);
    expect(page.items[0]).toMatchObject({
      id: "c1",
      status: "OPEN",
      status_label: "IN_PROGRESS",
      subject_label: "Örnek Üniversitesi",
      subject_still_pending: false,
    });
  });

  it("adminGetComplaint maps events and the closing reason", async () => {
    mockApiFetch.mockResolvedValueOnce({
      id: "c1",
      status: "UPHELD",
      subject_type: "ENGAGEMENT",
      subject_id: "e1",
      version: 4,
      resolution_reason: "Yanıt verilmedi",
      events: [{ id: "ev1", event_type: "UPHOLD", from_status: "ESCALATED", to_status: "UPHELD", note: null }],
    });
    const complaint = await adminGetComplaint("c1");
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/complaints/c1");
    expect(complaint.version).toBe(4);
    expect(complaint.result_reason).toBe("Yanıt verilmedi");
    expect(complaint.status_label).toBe("UPHELD");
    expect(complaint.events).toEqual([
      { id: "ev1", action: "UPHOLD", from_status: "ESCALATED", to_status: "UPHELD", note: null, created_at: null },
    ]);
  });

  it("adminTransition posts the action with reason and version", async () => {
    mockApiFetch.mockResolvedValueOnce({ id: "c1", status: "DISMISSED", subject_type: "ENGAGEMENT", subject_id: "e1" });
    await adminTransition("c1", { action: "DISMISS", reason: "Haksız", version: 2 });
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/complaints/c1/transitions", {
      method: "POST",
      body: { action: "DISMISS", reason: "Haksız", version: 2 },
    });
  });

  describe("uploadAttachment", () => {
    const file = new File(["%PDF-1.4"], "belge.pdf", { type: "application/pdf" });

    it("requests an upload slot, uploads to storage, then records the attachment", async () => {
      mockApiFetch
        .mockResolvedValueOnce({
          upload_url: "http://minio/bucket",
          upload_fields: { key: "complaints/c1/x.pdf" },
          object_key: "complaints/c1/x.pdf",
          expires_in: 300,
        })
        .mockResolvedValueOnce({ id: "f1", mime_type: "application/pdf", size_bytes: file.size });

      const result = await uploadAttachment("c1", file);

      expect(mockApiFetch).toHaveBeenNthCalledWith(1, "/complaints/c1/attachments/upload-url", {
        method: "POST",
        body: { filename: "belge.pdf", content_type: "application/pdf", size_bytes: file.size },
      });
      expect(mockStorageUpload).toHaveBeenCalledWith("http://minio/bucket", { key: "complaints/c1/x.pdf" }, file);
      expect(mockApiFetch).toHaveBeenNthCalledWith(2, "/complaints/c1/attachments", {
        method: "POST",
        body: { storage_key: "complaints/c1/x.pdf", mime_type: "application/pdf", size_bytes: file.size },
      });
      expect(result).toMatchObject({ id: "f1", filename: "belge.pdf" });
    });

    it("does not record the attachment when the storage upload fails", async () => {
      mockApiFetch.mockResolvedValueOnce({
        upload_url: "http://minio/bucket",
        upload_fields: {},
        object_key: "k",
        expires_in: 300,
      });
      mockStorageUpload.mockRejectedValueOnce(
        new ApiError({ status: 403, code: "STORAGE_UPLOAD_FAILED", message: "x", requestId: null }),
      );
      await expect(uploadAttachment("c1", file)).rejects.toMatchObject({ code: "STORAGE_UPLOAD_FAILED" });
      expect(mockApiFetch).toHaveBeenCalledTimes(1);
    });

    it("propagates a content rejection from the record step", async () => {
      mockApiFetch
        .mockResolvedValueOnce({ upload_url: "u", upload_fields: {}, object_key: "k", expires_in: 300 })
        .mockRejectedValueOnce(
          new ApiError({ status: 422, code: "INVALID_FILE_CONTENT", message: "bad", requestId: null }),
        );
      await expect(uploadAttachment("c1", file)).rejects.toMatchObject({ status: 422, code: "INVALID_FILE_CONTENT" });
    });
  });

  describe("getAttachmentDownloadUrl", () => {
    it("reads the signed url from the owner route", async () => {
      mockApiFetch.mockResolvedValueOnce({ download_url: "http://minio/signed", expires_in: 60 });
      expect(await getAttachmentDownloadUrl("c1", "f1")).toBe("http://minio/signed");
      expect(mockApiFetch).toHaveBeenCalledWith("/complaints/c1/attachments/f1");
    });

    it("uses the admin route when asked", async () => {
      mockApiFetch.mockResolvedValueOnce({ download_url: "http://minio/signed", expires_in: 60 });
      await getAttachmentDownloadUrl("c1", "f1", { admin: true });
      expect(mockApiFetch).toHaveBeenCalledWith("/admin/complaints/c1/attachments/f1");
    });

    it("throws when the response carries no url", async () => {
      mockApiFetch.mockResolvedValueOnce({});
      await expect(getAttachmentDownloadUrl("c1", "f1")).rejects.toBeInstanceOf(ApiError);
    });
  });
});
