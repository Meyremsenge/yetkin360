import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

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
    <Alert variant="error" className="text-sm">
      <div className="font-medium mb-2">{message}</div>

      <div className="flex items-center gap-4 mt-3">
        {requestId != null && (
          <div className="text-xs">
            {messages.errors.supportCode}
            {requestId ? `: ${requestId}` : ""}
          </div>
        )}

        {onRetry && (
          <Button onClick={onRetry} variant="destructive" size="sm">
            {messages.errors.retry}
          </Button>
        )}
      </div>
    </Alert>
  );
}
