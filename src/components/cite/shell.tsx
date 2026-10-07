import { Link, useRouterState } from "@tanstack/react-router";
import { Library, LogOut, MessageSquareQuote } from "lucide-react";
import type { ReactNode } from "react";

import { api } from "@/lib/cite/api";
import type { User } from "@/lib/cite/types";

const links = [
  { to: "/", label: "Library", icon: Library },
  { to: "/ask", label: "Ask", icon: MessageSquareQuote },
] as const;

export function Shell({
  user,
  onSignOut,
  children,
}: {
  user: User | null;
  onSignOut: () => void;
  children: ReactNode;
}) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  function signOut() {
    void api.logout().finally(onSignOut);
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <div className="mx-auto flex min-h-screen max-w-6xl">
        <aside className="hidden w-56 shrink-0 flex-col border-r border-line px-4 py-6 md:flex">
          <Brand />
          <nav className="mt-8 flex flex-col gap-1">
            {links.map((item) => (
              <NavLink key={item.to} {...item} active={pathname === item.to} />
            ))}
          </nav>
          <Account user={user} onSignOut={signOut} />
        </aside>
        <div className="flex min-w-0 flex-1 flex-col pb-20 md:pb-0">
          <header className="flex items-center justify-between border-b border-line px-4 py-3 md:hidden">
            <Brand />
            {user ? (
              <button type="button" className="h-11 px-2 text-sm text-muted" onClick={signOut}>
                Sign out
              </button>
            ) : null}
          </header>
          <main className="min-w-0 flex-1 px-4 py-5 md:px-8 md:py-7">{children}</main>
        </div>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-10 flex border-t border-line bg-sheet md:hidden">
        {links.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`flex h-14 flex-1 items-center justify-center gap-2 text-sm ${
              pathname === item.to ? "text-sienna" : "text-muted"
            }`}
          >
            <item.icon className="size-4" aria-hidden="true" />
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}

function Brand() {
  return (
    <Link to="/" className="flex items-baseline gap-2">
      <span className="font-serif text-2xl font-semibold tracking-tight">Cite</span>
      <span className="text-xs uppercase tracking-widest text-muted">library</span>
    </Link>
  );
}

function NavLink({
  to,
  label,
  icon: Icon,
  active,
}: {
  to: "/" | "/ask";
  label: string;
  icon: typeof Library;
  active: boolean;
}) {
  return (
    <Link
      to={to}
      className={`flex h-11 items-center gap-2 rounded-md px-3 text-sm ${
        active ? "bg-paper-2 text-ink" : "text-muted hover:bg-paper-2 hover:text-ink"
      }`}
    >
      <Icon className="size-4" aria-hidden="true" />
      {label}
    </Link>
  );
}

function Account({ user, onSignOut }: { user: User | null; onSignOut: () => void }) {
  return (
    <div className="mt-auto border-t border-line pt-4">
      {user ? (
        <>
          <p className="truncate text-sm">{user.email}</p>
          <button type="button" className="mt-2 flex h-11 items-center gap-2 text-sm text-muted hover:text-ink" onClick={onSignOut}>
            <LogOut className="size-4" aria-hidden="true" />
            Sign out
          </button>
        </>
      ) : (
        <Link to="/login" className="flex h-11 items-center text-sm text-sienna">
          Sign in
        </Link>
      )}
    </div>
  );
}

export function StatusMark({ status }: { status: "queued" | "ready" | "failed" }) {
  const styles = {
    queued: "bg-warn-bg text-warn",
    ready: "bg-ok-bg text-ok",
    failed: "bg-danger-bg text-danger",
  } as const;
  const label = { queued: "Queued", ready: "Ready", failed: "Failed" } as const;
  return (
    <span className={`inline-flex h-6 items-center rounded-sm px-2 text-xs font-medium ${styles[status]}`}>
      {label[status]}
    </span>
  );
}
