import { redirect } from "next/navigation";

export default function EvaluationPage() {
  // Redirect to the datasets page by default
  redirect("/evaluation/datasets");
}
