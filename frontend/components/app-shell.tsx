"use client";

import { ReactNode, RefObject, useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
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
import { SealMark } from "@/components/brand/brand-mark";
import { PAGE_CONTAINER } from "@/components/page-layout";
import messages from "@/messages/tr.json";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-1 focus-visible:ring-offset-card";
const OVERLAY_SHADOW = "shadow-[0_8px_24px_-12px_rgba(34,31,27,0.25)]";

// Discover page (/kesfet) is live.
const DISCOVER_ENABLED = true;

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
  compass: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z" />
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
  chevronDown: <path d="m6 9 6 6 6-6" />,
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

// "Ayşe Yılmaz" → "AY"; falls back to the e-mail's first letter.
function initialsOf(name: string | undefined, email: string | undefined): string {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length > 0) {
    const first = words[0].charAt(0);
    const last = words.length > 1 ? words[words.length - 1].charAt(0) : "";
    return `${first}${last}`.toLocaleUpperCase("tr-TR");
  }
  return email ? email.charAt(0).toLocaleUpperCase("tr-TR") : "?";
}

type Identity = {
  name: string | undefined;
  /** Second line under the name: role or organisation. */
  subtitle: string;
  email: string | undefined;
};

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

function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Closes a popover on outside click or Escape (focus returns to the trigger). */
function useDismiss(
  open: boolean,
  close: () => void,
  rootRef: RefObject<HTMLElement | null>,
  triggerRef: RefObject<HTMLElement | null>
) {
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) close();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close, rootRef, triggerRef]);
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
        "inline-flex shrink-0 items-center gap-2 rounded-md font-serif font-bold text-foreground",
        size === "md" ? "text-xl" : "text-lg",
        FOCUS_RING
      )}
    >
      <SealMark className={size === "md" ? "h-7 w-7" : "h-6 w-6"} />
      {messages.home.title}
    </Link>
  );
}

function Avatar({
  name,
  email,
  size = "md",
}: {
  name?: string;
  email: string | undefined;
  size?: "md" | "lg";
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full bg-success font-serif font-semibold text-background",
        size === "md" ? "h-9 w-9 text-[13px]" : "h-11 w-11 text-base"
      )}
    >
      {initialsOf(name, email)}
    </span>
  );
}

type NavData = {
  organizations: NamedRef[];
  institutions: NamedRef[];
  publicSlug: string | null;
  isAdmin: boolean;
  /** Organization/institution member without a talent profile: /calismalar lists students' engagements. */
  reviewsStudents: boolean;
};

type NavEntry = { href: string; icon: IconName; label: string };

function primaryLinks(data: NavData): NavEntry[] {
  return [
    {
      href: "/calismalar",
      icon: "briefcase",
      label: data.reviewsStudents ? messages.shell.studentEngagementsLink : messages.shell.engagementsLink,
    },
    { href: "/profil", icon: "user", label: messages.shell.profileLink },
    ...(DISCOVER_ENABLED ? [{ href: "/kesfet", icon: "compass" as const, label: messages.shell.discoverLink }] : []),
  ];
}

const ADMIN_LINKS: NavEntry[] = [
  { href: "/admin/dogrulama-kuyrugu", icon: "shield", label: messages.shell.adminVerificationQueueLink },
  { href: "/admin/skiller", icon: "tag", label: messages.shell.adminSkillsLink },
  { href: "/admin/sahtekarlik-isaretleri", icon: "shield", label: messages.shell.adminFraudQueueLink },
];

/** Role-specific destinations, grouped: organisations, institutions, admin. */
function contextGroups(data: NavData): { label: string; entries: NavEntry[] }[] {
  const groups = [
    {
      label: messages.shell.groupOrganizations,
      entries: data.organizations.map((org) => ({
        href: `/kurulus/${org.id}/panel`,
        icon: "building" as const,
        label: org.name,
      })),
    },
    {
      label: messages.shell.groupInstitutions,
      entries: data.institutions.map((inst) => ({
        href: `/kurum/${inst.id}/panel`,
        icon: "landmark" as const,
        label: inst.name,
      })),
    },
    { label: messages.shell.groupAdmin, entries: data.isAdmin ? ADMIN_LINKS : [] },
  ];
  return groups.filter((group) => group.entries.length > 0);
}

// "/kurulus/{id}/panel" is active for every page under "/kurulus/{id}".
function sectionOf(href: string): string {
  return href.replace(/\/panel$/, "");
}

/* ------------------------------------------------------------------ */
/* Desktop top bar (≥1024px)                                           */
/* ------------------------------------------------------------------ */

function TopNavLink({ entry, active }: { entry: NavEntry; active: boolean }) {
  return (
    <li className="flex">
      <Link
        href={entry.href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "relative flex items-center gap-2 rounded-md px-3 text-sm transition-colors duration-[120ms]",
          "after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:rounded-full after:transition-colors",
          active
            ? "font-medium text-foreground after:bg-success"
            : "text-muted-foreground after:bg-transparent hover:text-foreground hover:after:bg-border",
          FOCUS_RING
        )}
      >
        <Icon name={entry.icon} className={active ? "text-success" : undefined} />
        {entry.label}
      </Link>
    </li>
  );
}

/**
 * Organisation/institution members can belong to several entities: one
 * switcher lists them all plus admin screens. The list stays mounted and is
 * toggled with CSS so its links are real DOM nodes.
 */
function ContextSwitcher({ data, pathname }: { data: NavData; pathname: string }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listId = useId();
  useDismiss(open, () => setOpen(false), rootRef, triggerRef);

  const groups = contextGroups(data);
  if (groups.length === 0) return null;

  const current = groups
    .flatMap((group) => group.entries)
    .find((entry) => isActivePath(pathname, sectionOf(entry.href)));

  return (
    <div ref={rootRef} className="relative flex items-center">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex h-9 max-w-[240px] items-center gap-2 rounded-md border px-3 text-sm transition-colors duration-[120ms]",
          current
            ? "border-success/25 bg-success/[0.06] font-medium text-foreground"
            : "border-border bg-background text-muted-foreground hover:text-foreground",
          FOCUS_RING
        )}
      >
        <span className="sr-only">{messages.shell.contextSwitcher}: </span>
        <Icon name={current?.icon ?? "building"} className={current ? "text-success" : undefined} />
        <span className="min-w-0 truncate">{current?.label ?? messages.shell.contextPanels}</span>
        <Icon
          name="chevronDown"
          className={cn("h-3.5 w-3.5 transition-transform duration-[120ms]", open && "rotate-180")}
        />
      </button>

      <div
        id={listId}
        className={cn(
          "y360-step-in absolute left-0 top-full z-50 mt-2 max-h-[70vh] w-[300px] overflow-y-auto rounded-xl border border-border bg-card p-1.5",
          OVERLAY_SHADOW,
          !open && "hidden"
        )}
      >
        {groups.map((group) => (
          <ContextGroup key={group.label} label={group.label}>
            {group.entries.map((entry) => {
              const active = isActivePath(pathname, sectionOf(entry.href));
              return (
                <li key={entry.href}>
                  <Link
                    href={entry.href}
                    title={entry.label}
                    aria-current={active ? "page" : undefined}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex h-10 items-center gap-2.5 rounded-md px-3 text-sm transition-colors duration-[120ms]",
                      active
                        ? "bg-success/[0.08] font-medium text-success"
                        : "text-foreground hover:bg-muted/60",
                      FOCUS_RING
                    )}
                  >
                    <Icon name={entry.icon} className={active ? "text-success" : "text-muted-foreground"} />
                    <span className="min-w-0 flex-1 truncate">{entry.label}</span>
                  </Link>
                </li>
              );
            })}
          </ContextGroup>
        ))}
      </div>
    </div>
  );
}

function ContextGroup({ label, children }: { label: string; children: ReactNode }) {
  const id = useId();
  return (
    <div className="py-1 [&+&]:border-t [&+&]:border-border">
      <p id={id} className="px-3 pb-1 pt-1.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <ul aria-labelledby={id}>{children}</ul>
    </div>
  );
}

/** Avatar + menu. The list stays mounted and is toggled with CSS. */
function UserMenu({ identity, onLogout }: { identity: Identity; onLogout: () => void }) {
  const { name, subtitle, email } = identity;
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();
  const masked = maskEmail(email);
  useDismiss(open, () => setOpen(false), rootRef, triggerRef);

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-label={messages.shell.userMenu}
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex h-10 items-center gap-1.5 rounded-full p-0.5 transition-colors duration-[120ms] lg:pr-2",
          open ? "bg-muted" : "hover:bg-muted/60",
          FOCUS_RING
        )}
      >
        <Avatar name={name} email={email} />
        <Icon name="chevronDown" className="hidden h-3.5 w-3.5 text-muted-foreground lg:block" />
      </button>

      <div
        id={menuId}
        className={cn(
          "y360-step-in absolute right-0 top-full z-50 mt-2 w-[260px] overflow-hidden rounded-xl border border-border bg-card",
          OVERLAY_SHADOW,
          !open && "hidden"
        )}
      >
        <div className="flex items-center gap-3 border-b border-border bg-sand/50 px-4 py-3.5">
          <Avatar name={name} email={email} size="lg" />
          <div className="min-w-0">
            <p className="truncate font-serif text-[15px] font-semibold text-foreground">{name ?? masked}</p>
            <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
            <p className="truncate font-mono text-[11px] text-muted-foreground">{masked}</p>
          </div>
        </div>
        <div className="p-1.5">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
            className={cn(
              "flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm text-destructive transition-colors duration-[120ms] hover:bg-destructive/10",
              FOCUS_RING
            )}
          >
            <Icon name="logOut" />
            {messages.session.logout}
          </button>
        </div>
      </div>
    </div>
  );
}

function PublicProfileLink({ slug }: { slug: string }) {
  return (
    <Link
      href={`/p/${encodeURIComponent(slug)}`}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "hidden h-9 items-center gap-1.5 rounded-md border border-border px-3 text-sm font-medium text-foreground transition-colors duration-[120ms] hover:border-success/40 hover:bg-success/[0.06] md:inline-flex",
        FOCUS_RING
      )}
    >
      {messages.shell.viewPublicProfile}
      <Icon name="arrowUpRight" className="h-3.5 w-3.5 text-success" />
      <span className="sr-only">{messages.shell.newTab}</span>
    </Link>
  );
}

/* ------------------------------------------------------------------ */
/* Mobile drawer (<1024px)                                             */
/* ------------------------------------------------------------------ */

function DrawerItem({
  entry,
  active,
  external,
  onNavigate,
}: {
  entry: NavEntry;
  active: boolean;
  external?: boolean;
  onNavigate: () => void;
}) {
  return (
    <li className="relative">
      {active && (
        <span aria-hidden="true" className="absolute -left-2 top-1/2 h-5 w-0.5 -translate-y-1/2 bg-success" />
      )}
      <Link
        href={entry.href}
        onClick={onNavigate}
        title={entry.label}
        aria-current={active ? "page" : undefined}
        target={external ? "_blank" : undefined}
        rel={external ? "noopener noreferrer" : undefined}
        className={cn(
          "flex h-10 items-center gap-2.5 rounded-md border px-3 text-sm transition-colors duration-[120ms]",
          active
            ? "border-success/15 bg-success/[0.08] font-medium text-success"
            : "border-transparent text-muted-foreground hover:bg-muted/60 hover:text-foreground",
          FOCUS_RING
        )}
      >
        <Icon name={entry.icon} className={active ? "text-success" : undefined} />
        <span className="min-w-0 flex-1 truncate">{entry.label}</span>
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

function DrawerGroup({ label, children }: { label: string; children: ReactNode }) {
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
          "absolute inset-y-0 left-0 flex w-[280px] max-w-[85vw] flex-col overflow-y-auto border-r border-border bg-card",
          OVERLAY_SHADOW
        )}
      >
        <div className="flex items-center justify-between gap-2 px-5 pb-5 pt-6">
          <Logo />
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
        </div>
        <div aria-hidden="true" className="mx-5 h-px bg-border" />
        <nav aria-label={messages.shell.mainNav} className="pb-6">
          <DrawerGroup label={messages.shell.groupWork}>
            {primaryLinks(data).map((entry) => (
              <DrawerItem
                key={entry.href}
                entry={entry}
                active={isActivePath(pathname, entry.href)}
                onNavigate={onClose}
              />
            ))}
            {data.publicSlug && (
              <DrawerItem
                entry={{
                  href: `/p/${encodeURIComponent(data.publicSlug)}`,
                  icon: "globe",
                  label: messages.shell.publicProfileLink,
                }}
                active={false}
                external
                onNavigate={onClose}
              />
            )}
          </DrawerGroup>
          {contextGroups(data).map((group) => (
            <DrawerGroup key={group.label} label={group.label}>
              {group.entries.map((entry) => (
                <DrawerItem
                  key={entry.href}
                  entry={entry}
                  active={isActivePath(pathname, sectionOf(entry.href))}
                  onNavigate={onClose}
                />
              ))}
            </DrawerGroup>
          ))}
        </nav>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shell states                                                        */
/* ------------------------------------------------------------------ */

function SkeletonBar({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-md bg-muted", className)} />;
}

function ShellLoading() {
  return (
    <div aria-busy="true" className="min-h-screen bg-background">
      <span role="status" className="sr-only">
        {messages.shell.loading}
      </span>
      <div className="border-b border-border bg-card">
        <div className={cn(PAGE_CONTAINER, "flex h-14 items-center gap-6 lg:h-16")}>
          <SkeletonBar className="h-7 w-32" />
          <div className="hidden items-center gap-4 lg:flex">
            {[0, 1, 2].map((i) => (
              <SkeletonBar key={i} className="h-4 w-24" />
            ))}
          </div>
          <SkeletonBar className="ml-auto h-9 w-9 rounded-full" />
        </div>
      </div>
      <div className="border-b border-border bg-card">
        <div className={cn(PAGE_CONTAINER, "py-8")}>
          <SkeletonBar className="h-3 w-24" />
          <SkeletonBar className="mt-3 h-8 w-64" />
        </div>
      </div>
      <div className={cn(PAGE_CONTAINER, "space-y-4 pt-8")}>
        {[0, 1, 2].map((i) => (
          <SkeletonBar key={i} className="h-24 w-full" />
        ))}
      </div>
    </div>
  );
}

// Session/error states: logo only, error card top-left (brief §5.4).
function ShellErrorFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className={cn(PAGE_CONTAINER, "flex h-14 items-center lg:h-16")}>
          <Logo />
        </div>
      </header>
      <main className={PAGE_CONTAINER}>
        <div className="max-w-[600px] pt-8">{children}</div>
      </main>
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
  const profileName = data?.talent_profile?.full_name;
  const displayName =
    (typeof profileName === "string" && profileName.trim()) || data?.user.full_name?.trim() || undefined;
  const firstEntity = data ? namedRefs(data.organizations)[0] ?? namedRefs(data.institutions)[0] : undefined;
  const identity: Identity = {
    name: displayName,
    // An entity membership says more than "student" (seed org admins also
    // have a talent profile).
    subtitle:
      firstEntity?.name ??
      (data?.talent_profile
        ? messages.shell.roleStudent
        : data?.user.is_platform_admin
          ? messages.shell.roleAdmin
          : maskEmail(data?.user.email)),
    email: data?.user.email,
  };
  const navData: NavData | null = data
    ? {
        organizations: namedRefs(data.organizations),
        institutions: namedRefs(data.institutions),
        publicSlug: data.talent_profile?.public_slug ?? null,
        isAdmin: data.user.is_platform_admin === true,
        reviewsStudents:
          !data.talent_profile && namedRefs(data.organizations).length + namedRefs(data.institutions).length > 0,
      }
    : null;

  // AC-5: error with cached data → banner above content
  const cachedError = Boolean(session.error) && data ? describeError(session.error) : null;
  const showEmailBanner = Boolean(data) && data?.user.email_verified === false;
  // AC-12: empty organizations is an info state, not an error. Students,
  // institution members and admins don't need an organization (brief §5.3).
  const showNoOrganizations =
    Boolean(data) &&
    data?.organizations.length === 0 &&
    !data.talent_profile &&
    data.institutions.length === 0 &&
    data.user.is_platform_admin !== true;
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
          <header className="sticky top-0 z-40 border-b border-border bg-card">
            <div className={cn(PAGE_CONTAINER, "flex h-14 items-center gap-3 lg:h-16 lg:gap-6")}>
              <button
                ref={menuButtonRef}
                type="button"
                aria-label={messages.shell.openMenu}
                aria-expanded={drawerOpen}
                onClick={() => setDrawerOpen(true)}
                className={cn(
                  "-ml-2 flex h-10 w-10 items-center justify-center rounded-md text-foreground hover:bg-muted lg:hidden",
                  FOCUS_RING
                )}
              >
                <Icon name="menu" className="h-5 w-5" />
              </button>
              <Logo />

              <nav aria-label={messages.shell.mainNav} className="hidden h-full items-stretch gap-4 lg:flex">
                <ul className="flex items-stretch">
                  {primaryLinks(navData).map((entry) => (
                    <TopNavLink key={entry.href} entry={entry} active={isActivePath(pathname, entry.href)} />
                  ))}
                </ul>
                {contextGroups(navData).length > 0 && (
                  <>
                    <span aria-hidden="true" className="my-5 w-px bg-border" />
                    <ContextSwitcher data={navData} pathname={pathname} />
                  </>
                )}
              </nav>

              <div className="ml-auto flex items-center gap-3">
                {navData.publicSlug && <PublicProfileLink slug={navData.publicSlug} />}
                <UserMenu identity={identity} onLogout={() => logoutState.logout()} />
              </div>
            </div>
          </header>

          {drawerOpen && <MobileDrawer data={navData} pathname={pathname} onClose={closeDrawer} />}
        </>
      )}

      {hasBanners && (
        <div className={cn(PAGE_CONTAINER, "space-y-2 pt-6")}>
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
  );
}
