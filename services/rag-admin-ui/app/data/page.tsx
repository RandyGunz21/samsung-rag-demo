import { redirect } from "next/navigation";

export default function DataPage() {
  // Redirect to the upload page by default
  redirect("/data/upload");
}
