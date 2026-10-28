import { notFound } from "next/navigation";
/** No privileged operator screen without verified server-side identity. */
export default function OperatorLayout(): never { return notFound(); }
