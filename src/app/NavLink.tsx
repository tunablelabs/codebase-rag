"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ComponentProps } from "react";

export default function NavLink(props: ComponentProps<typeof Link>) {
  const pathname = usePathname();

  return <Link {...props} data-active={pathname === props.href || undefined} />;
}
