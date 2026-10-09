export function VerifiedSeal({
  name,
  issuedAt,
  registryNo,
}: {
  name?: string;
  issuedAt?: string;
  registryNo?: string;
}) {
  return (
    <div data-testid="verified-seal" className="flex flex-col items-center gap-4 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-full bg-success text-background">
        <svg
          viewBox="0 0 24 24"
          className="h-8 w-8"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path d="M5 12l5 5L20 7" />
        </svg>
      </span>
      {name ? <p className="font-serif text-2xl">{name}</p> : null}
      {issuedAt ? <p className="font-mono text-sm">{issuedAt}</p> : null}
      {registryNo ? <p className="font-mono text-sm">{registryNo}</p> : null}
    </div>
  );
}
