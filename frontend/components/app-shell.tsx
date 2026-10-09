"use client";

import { ReactNode, useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { useSession, useLogout } from "@/lib/session/use-session";
import { ErrorBanner } from "@/components/error-banner";
import { EmailVerificationBanner } from "@/components/email-verification-banner";
import {
  NetworkError,
  ApiError,
  SessionExpiredError,
  InvalidResponseError,
} from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-1 focus-visible:ring-offset-sand";
const CONTENT_GUTTER = "px-4 md:px-6 lg:px-10";
const OVERLAY_SHADOW = "shadow-[0_8px_24px_-12px_rgba(34,31,27,0.25)]";

// Inline lucide paths (no icon dependency, brief §1.5).
const ICON_PATHS = {
  briefcase: (
    <>
      <path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      <rect width="20" height="14" x="2" y="6" rx="2" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="5" />
      <path d="M20 21a8 8 0 0 0-16 0" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
      <path d="M2 12h20" />
    </>
  ),
  building: (
    <>
      <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" />
      <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
      <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2" />
    </>
  ),
  landmark: (
    <>
      <path d="M3 22h18" />
      <path d="M6 18v-7M10 18v-7M14 18v-7M18 18v-7" />
      <path d="M12 2 20 7H4z" />
    </>
  ),
  shield: (
    <>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  tag: (
    <>
      <path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" />
      <circle cx="7.5" cy="7.5" r="1" />
    </>
  ),
  arrowUpRight: (
    <>
      <path d="M7 7h10v10" />
      <path d="M7 17 17 7" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  close: <path d="M18 6 6 18M6 6l12 12" />,
  chevronsUpDown: (
    <>
      <path d="m7 15 5 5 5-5" />
      <path d="m7 9 5-5 5 5" />
    </>
  ),
  logOut: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
    </>
  ),
};

type IconName = keyof typeof ICON_PATHS;

function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("h-4 w-4 shrink-0", className)}
    >
      {ICON_PATHS[name]}
    </svg>
  );
}

// Never show the full address (brief §5.1): "meyr…@gmail.com".
function maskEmail(email: string | undefined): string {
  if (!email) return "";
  const at = email.indexOf("@");
  if (at < 1) return "";
  const local = email.slice(0, at);
  const keep = Math.max(1, Math.min(4, local.length - 1));
  return `${local.slice(0, keep)}…${email.slice(at)}`;
}

function initialOf(email: string | undefined): string {
  return email ? email.charAt(0).toLocaleUpperCase("tr-TR") : "?";
}

type NamedRef = { id: string; name: string };

function namedRefs(items: unknown[]): NamedRef[] {
  return items.filter(
    (item): item is NamedRef =>
      typeof item === "object" &&
      item !== null &&
      typeof (item as NamedRef).id === "string" &&
      typeof (item as NamedRef).name === "string"
  );
}

// Every page mounts its own AppShell, so the path is read once per page; no
// dependency on next/navigation (page tests mock that module partially).
function subscribePath(onChange: () => void) {
  window.addEventListener("popstate", onChange);
  return () => window.removeEventListener("popstate", onChange);
}

function useCurrentPath(): string {
  return useSyncExternalStore(
    subscribePath,
    () => window.location.pathname,
    () => ""
  );
}

function describeError(error: unknown): { message: string; requestId?: string } {
  if (error instanceof NetworkError) {
    return {
      message: error.kind === "timeout" ? messages.errors.timeout : messages.errors.network,
    };
  }
  if (error instanceof ApiError) {
    return { message: messages.errors.generic, requestId: error.requestId || undefined };
  }
  return { message: messages.errors.generic };
}

function Logo({ size = "md" }: { size?: "md" | "sm" }) {
  return (
    <Link
      href="/calismalar"
      className={cn(
        "rounded-md font-serif font-bold text-foreground",
        size === "md" ? "text-xl" : "text-lg",
        FOCUS_RING
      )}
    >
      {messages.home.title}
    </Link>
  );
}

function Avatar({ email }: { email: string | undefined }) {
  return (
    <span
      aria-hidden="true"
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-card font-serif text-sm font-semibold text-foreground"
    >
      {initialOf(email)}
    </span>
  );
}

function NavItem({
  href,
  icon,
  label,
  active,
  external,
  onNavigate,
}: {
  href: string;
  icon: IconName;
  label: string;
  active: boolean;
  external?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <li className="relative">
      {active && (
        <span aria-hidden="true" className="absolute -left-2 top-1/2 h-5 w-0.5 -translate-y-1/2 bg-success" />
      )}
      <Link
        href={href}
        onClick={onNavigate}
        title={label}
        aria-current={active ? "page" : undefined}
        target={external ? "_blank" : undefined}
        rel={external ? "noopener noreferrer" : undefined}
        className={cn(
          "flex h-9 items-center gap-2.5 rounded-md border px-3 text-sm transition-colors duration-[120ms]",
          active
            ? "border-border bg-card font-medium text-foreground"
            : "border-transparent text-muted-foreground hover:bg-background hover:text-foreground",
          FOCUS_RING
        )}
      >
        <Icon name={icon} className={active ? "text-success" : undefined} />
        <span className="min-w-0 flex-1 truncate">{label}</span>
        {external && (
          <>
            <Icon name="arrowUpRight" className="h-3.5 w-3.5" />
            <span className="sr-only">{messages.shell.newTab}</span>
          </>
        )}
      </Link>
    </li>
  );
}

function NavGroup({ label, children }: { label: string; children: ReactNode }) {
  const id = useId();
  return (
    <div className="mt-6">
      <p id={id} className="mb-2 px-5 text-xs font-medium text-muted-foreground">
        {label}
      </p>
      <ul aria-labelledby={id} className="space-y-0.5 px-2">
        {children}
      </ul>
    </div>
  );
}

type NavData = {
  organizations: NamedRef[];
  institutions: NamedRef[];
  publicSlug: string | null;
  isAdmin: boolean;
};

function NavLinks({
  data,
  pathname,
  onNavigate,
}: {
  data: NavData;
  pathname: string;
  onNavigate?: () => void;
}) {
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  return (
    <>
      <NavGroup label={messages.shell.groupWork}>
        <NavItem
          href="/calismalar"
          icon="briefcase"
          label={messages.shell.engagementsLink}
          active={isActive("/calismalar")}
          onNavigate={onNavigate}
        />
        <NavItem
          href="/profil"
          icon="user"
          label={messages.shell.profileLink}
          active={isActive("/profil")}
          onNavigate={onNavigate}
        />
        {data.publicSlug && (
          <NavItem
            href={`/p/${encodeURIComponent(data.publicSlug)}`}
            icon="globe"
            label={messages.shell.publicProfileLink}
            active={false}
            external
            onNavigate={onNavigate}
          />
        )}
      </NavGroup>

      {data.organizations.length > 0 && (
        <NavGroup label={messages.shell.groupOrganizations}>
          {data.organizations.map((org) => (
            <NavItem
              key={org.id}
              href={`/kurulus/${org.id}/panel`}
              icon="building"
              label={org.name}
              active={isActive(`/kurulus/${org.id}`)}
              onNavigate={onNavigate}
            />
          ))}
        </NavGroup>
      )}

      {data.institutions.length > 0 && (
        <NavGroup label={messages.shell.groupInstitutions}>
          {data.institutions.map((inst) => (
            <NavItem
              key={inst.id}
              href={`/kurum/${inst.id}/panel`}
              icon="landmark"
              label={inst.name}
              active={isActive(`/kurum/${inst.id}`)}
              onNavigate={onNavigate}
            />
          ))}
        </NavGroup>
      )}

      {data.isAdmin && (
        <NavGroup label={messages.shell.groupAdmin}>
          <NavItem
            href="/admin/dogrulama-kuyrugu"
            icon="shield"
            label={messages.shell.adminVerificationQueueLink}
            active={isActive("/admin/dogrulama-kuyrugu")}
            onNavigate={onNavigate}
          />
          <NavItem
            href="/admin/skiller"
            icon="tag"
            label={messages.shell.adminSkillsLink}
            active={isActive("/admin/skiller")}
            onNavigate={onNavigate}
          />
        </NavGroup>
      )}
    </>
  );
}

function SidebarHeader({ trailing }: { trailing?: ReactNode }) {
  return (
    <div className="px-5 pb-5 pt-6">
      <div className="flex items-start justify-between gap-2">
        <Logo />
        {trailing}
      </div>
      <p className="mt-1 font-mono text-[11px] leading-4 text-muted-foreground">
        {messages.home.tagline}
      </p>
    </div>
  );
}

/**
 * User card + menu. `variant="sidebar"` keeps the list mounted and toggles it
 * with CSS so it is a real DOM node; `variant="topbar"` mounts it on open.
 */
function UserMenu({
  email,
  onLogout,
  variant,
}: {
  email: string | undefined;
  onLogout: () => void;
  variant: "sidebar" | "topbar";
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();
  const masked = maskEmail(email);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const list = (
    <ul
      id={menuId}
      className={cn(
        "absolute z-50 min-w-[200px] rounded-lg border border-border bg-card p-1",
        OVERLAY_SHADOW,
        variant === "sidebar" ? "bottom-full left-0 right-0 mb-2" : "right-0 top-full mt-2",
        variant === "sidebar" && !open && "hidden"
      )}
    >
      <li>
        <Link
          href="/profil"
          onClick={() => setOpen(false)}
          className={cn(
            "flex h-9 items-center gap-2 rounded-md px-3 text-sm text-foreground hover:bg-muted",
            FOCUS_RING
          )}
        >
          <Icon name="user" className="text-muted-foreground" />
          {messages.shell.profileLink}
        </Link>
      </li>
      <li aria-hidden="true" className="my-1 h-px bg-border" />
      <li>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            onLogout();
          }}
          className={cn(
            "flex h-9 w-full items-center gap-2 rounded-md px-3 text-left text-sm text-destructive hover:bg-destructive/10",
            FOCUS_RING
          )}
        >
          <Icon name="logOut" />
          {messages.session.logout}
        </button>
      </li>
    </ul>
  );

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-label={variant === "topbar" ? messages.shell.userMenu : undefined}
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          variant === "sidebar"
            ? "flex h-14 w-full items-center gap-3 rounded-md px-2 text-left hover:bg-background/60"
            : "flex h-10 w-10 items-center justify-center rounded-full",
          FOCUS_RING
        )}
      >
        <Avatar email={email} />
        {variant === "sidebar" && (
          <>
            <span className="min-w-0 flex-1">
              <span className="sr-only">{messages.shell.userMenu}: </span>
              <span className="block truncate text-sm font-medium text-foreground">{masked}</span>
            </span>
            <Icon name="chevronsUpDown" className="text-muted-foreground" />
          </>
        )}
      </button>
      {(variant === "sidebar" || open) && list}
    </div>
  );
}

function MobileDrawer({
  data,
  pathname,
  onClose,
}: {
  data: NavData;
  pathname: string;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      // Keep focus inside the drawer (brief §5.2).
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>("a[href], button");
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div aria-hidden="true" onClick={onClose} className="absolute inset-0 bg-foreground/40" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={messages.shell.mainNav}
        className={cn(
          "absolute inset-y-0 left-0 flex w-[280px] max-w-[85vw] flex-col overflow-y-auto border-r border-border bg-sand",
          OVERLAY_SHADOW
        )}
      >
        <SidebarHeader
          trailing={
            <button
              ref={closeRef}
              type="button"
              aria-label={messages.shell.closeMenu}
              onClick={onClose}
              className={cn(
                "-mr-2 -mt-1 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-background hover:text-foreground",
                FOCUS_RING
              )}
            >
              <Icon name="close" />
            </button>
          }
        />
        <div aria-hidden="true" className="mx-5 h-px bg-border" />
        <nav aria-label={messages.shell.mainNav} className="pb-6">
          <NavLinks data={data} pathname={pathname} onNavigate={onClose} />
        </nav>
      </div>
    </div>
  );
}

function SkeletonBar({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-md bg-muted", className)} />;
}

function ShellLoading() {
  return (
    <div aria-busy="true" className="min-h-screen bg-background">
      <span role="status" className="sr-only">
        {messages.shell.loading}
      </span>
      <aside className="fixed inset-y-0 left-0 hidden w-[248px] flex-col border-r border-border bg-sand px-5 pb-3 pt-6 lg:flex">
        <SkeletonBar className="h-6 w-28 bg-background" />
        <SkeletonBar className="mt-2 h-3 w-40 bg-background" />
        <div className="mt-10 space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonBar key={i} className="h-7 w-full bg-background" />
          ))}
        </div>
        <div className="mt-auto flex items-center gap-3 border-t border-border pt-3">
          <SkeletonBar className="h-8 w-8 rounded-full bg-background" />
          <SkeletonBar className="h-3 w-24 bg-background" />
        </div>
      </aside>
      <div className="h-14 border-b border-border lg:hidden" />
      <div className={cn("lg:pl-[248px]")}>
        <div className={cn(CONTENT_GUTTER, "max-w-[1040px] pt-8")}>
          <SkeletonBar className="h-8 w-64" />
          <div className="mt-8 space-y-4">
            {[0, 1, 2].map((i) => (
              <SkeletonBar key={i} className="h-24 w-full" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Session/error states: logo only, error card top-left (brief §5.4).
function ShellErrorFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <header className={cn(CONTENT_GUTTER, "flex h-14 items-center border-b border-border bg-sand lg:h-16")}>
        <Logo />
      </header>
      <main className={cn(CONTENT_GUTTER, "max-w-[600px] pt-8")}>{children}</main>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const session = useSession();
  const logoutResult = useLogout();
  const logout = logoutResult || { logout: () => {}, isPending: false, isError: false };
  const logoutState = logout as ReturnType<typeof useLogout>;
  const pathname = useCurrentPath();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  // AC-1: Loading state
  if (session.isPending) {
    return <ShellLoading />;
  }

  // AC-S1: SessionExpiredError → no children rendered
  if (session.error instanceof SessionExpiredError) {
    return (
      <ShellErrorFrame>
        <ErrorBanner message={messages.session.expired} onRetry={() => session.refetch()} />
        <Link
          href="/giris"
          className={cn(
            "mt-4 inline-flex h-10 items-center rounded-md bg-success px-4 text-sm font-medium text-background hover:bg-success/90",
            FOCUS_RING
          )}
        >
          {messages.shell.signIn}
        </Link>
      </ShellErrorFrame>
    );
  }

  // AC-7: InvalidResponseError
  if (session.error instanceof InvalidResponseError) {
    return (
      <ShellErrorFrame>
        <ErrorBanner message={messages.session.loadFailed} onRetry={() => session.refetch()} />
      </ShellErrorFrame>
    );
  }

  // AC-5: NetworkError or 5xx with no data → error screen
  if (session.error && !session.data) {
    const { message, requestId } = describeError(session.error);
    return (
      <ShellErrorFrame>
        <ErrorBanner message={message} requestId={requestId} onRetry={() => session.refetch()} />
      </ShellErrorFrame>
    );
  }

  const data = session.data;
  const navData: NavData | null = data
    ? {
        organizations: namedRefs(data.organizations),
        institutions: namedRefs(data.institutions),
        publicSlug: data.talent_profile?.public_slug ?? null,
        isAdmin: data.user.is_platform_admin === true,
      }
    : null;

  // AC-5: error with cached data → banner above content
  const cachedError = Boolean(session.error) && data ? describeError(session.error) : null;
  const showEmailBanner = Boolean(data) && data?.user.email_verified === false;
  // AC-12: empty organizations is an info state, not an error
  const showNoOrganizations = Boolean(data) && data?.organizations.length === 0;
  const showLogoutError = logoutState.isError;
  const hasBanners = Boolean(cachedError) || showEmailBanner || showNoOrganizations || showLogoutError;

  const closeDrawer = () => {
    setDrawerOpen(false);
    menuButtonRef.current?.focus();
  };

  return (
    <div className="min-h-screen bg-background">
      {data && navData && (
        <>
          {/* Desktop sidebar (≥1024px) */}
          <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-border bg-sand lg:flex">
            <SidebarHeader />
            <div aria-hidden="true" className="mx-5 h-px bg-border" />
            <nav aria-label={messages.shell.mainNav} className="flex-1 overflow-y-auto pb-6">
              <NavLinks data={navData} pathname={pathname} />
            </nav>
            <div className="border-t border-border p-3">
              <UserMenu email={data.user.email} onLogout={() => logoutState.logout()} variant="sidebar" />
            </div>
          </aside>

          {/* Mobile/tablet top bar (<1024px) */}
          <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background px-4 lg:hidden">
            <div className="flex items-center gap-3">
              <button
                ref={menuButtonRef}
                type="button"
                aria-label={messages.shell.openMenu}
                aria-expanded={drawerOpen}
                onClick={() => setDrawerOpen(true)}
                className={cn(
                  "-ml-2 flex h-10 w-10 items-center justify-center rounded-md text-foreground hover:bg-muted",
                  FOCUS_RING
                )}
              >
                <Icon name="menu" className="h-5 w-5" />
              </button>
              <Logo size="sm" />
            </div>
            <UserMenu email={data.user.email} onLogout={() => logoutState.logout()} variant="topbar" />
          </header>

          {drawerOpen && <MobileDrawer data={navData} pathname={pathname} onClose={closeDrawer} />}
        </>
      )}

      <div className={cn(data && "lg:pl-[248px]")}>
        {hasBanners && (
          <div className={cn(CONTENT_GUTTER, "max-w-[1120px] space-y-2 pt-6")}>
            {cachedError && (
              <ErrorBanner
                message={cachedError.message}
                requestId={cachedError.requestId}
                onRetry={() => session.refetch()}
              />
            )}

            {/* YET-196: unverified e-mail -> explain the 401 and offer a new link */}
            {showEmailBanner && <EmailVerificationBanner />}

            {showNoOrganizations && (
              <p className="rounded-md border border-border bg-muted px-4 py-3 text-sm text-muted-foreground">
                {messages.shell.noOrganizations}
              </p>
            )}

            {/* AC-8: Logout error */}
            {showLogoutError && <ErrorBanner message={messages.session.logoutFailed} />}
          </div>
        )}

        {/* AC-1: Children render */}
        <div>{children}</div>
      </div>
    </div>
  );
}
