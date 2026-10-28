import { notFound } from "next/navigation";
/** No workspace data may be served until IAM and session grants are verified. */
export default function WorkspaceLayout(): never { return notFound(); }
