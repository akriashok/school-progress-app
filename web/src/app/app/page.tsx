"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { homeFor, useMe } from "@/lib/auth";
import { Spinner } from "@/components/ui/misc";

export default function AppHome() {
  const me = useMe();
  const router = useRouter();
  React.useEffect(() => router.replace(homeFor(me.role)), [me.role, router]);
  return <Spinner />;
}
