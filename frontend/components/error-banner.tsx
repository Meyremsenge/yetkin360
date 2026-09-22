import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";

export function ErrorBanner({
  message,
  requestId,
  onRetry,
}: {
  message: string;
  requestId?: string | null;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
      <div className="font-medium mb-2">{message}</div>

      <div className="flex items-center gap-4 mt-3">
        {requestId != null && (
          <div className="text-xs">
            {messages.errors.supportCode}
            {requestId ? `: ${requestId}` : ""}
          </div>
        )}

        {onRetry && (
          <Button
            onClick={onRetry}
            className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 text-sm"
          >
            {messages.errors.retry}
          </Button>
        )}
      </div>
    </div>
  );
}
