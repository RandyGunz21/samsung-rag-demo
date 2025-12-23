"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { GroundTruthEditor } from "@/components/evaluation/ground-truth-editor";
import { useEvaluationStore } from "@/lib/stores";
import type { TestDataset } from "@/lib/types";

export default function EditDatasetPage() {
  const params = useParams();
  const datasetId = params.id as string;
  const { fetchDataset } = useEvaluationStore();
  const [dataset, setDataset] = useState<TestDataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const loadDataset = async () => {
      try {
        const data = await fetchDataset(datasetId);
        setDataset(data);
      } catch (err) {
        console.error("Failed to load dataset:", err);
      } finally {
        setLoading(false);
      }
    };

    loadDataset();
  }, [datasetId, fetchDataset]);

  if (!mounted) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
        <p className="ml-4 text-muted-foreground">Loading dataset...</p>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Dataset not found</p>
      </div>
    );
  }

  return <GroundTruthEditor mode="edit" dataset={dataset} />;
}
