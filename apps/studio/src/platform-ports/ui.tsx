import type { ReactNode } from "react";
/** I00 placeholder; A02 owns final UI library. */
export function UnavailableState({children}:{children?:ReactNode}) {return <section role="status">{children ?? "Источник не подключён."}</section>}
