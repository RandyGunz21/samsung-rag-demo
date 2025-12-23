"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, Trash2, Edit, FileText, AlertCircle } from "lucide-react";
import { useEvaluationStore } from "@/lib/stores";
import type { DatasetListItem } from "@/lib/types";

export default function DatasetsPage() {
  const router = useRouter();
  const { datasets, isLoading, error, fetchDatasets, deleteDataset } = useEvaluationStore();
  const [mounted, setMounted] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    fetchDatasets();
  }, [fetchDatasets]);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this dataset?")) {
      return;
    }

    setDeleting(id);
    try {
      await deleteDataset(id);
    } catch (err) {
      console.error("Failed to delete dataset:", err);
    } finally {
      setDeleting(null);
    }
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Test Datasets</h1>
          <p className="text-muted-foreground">
            Manage test datasets with ground truth for evaluation
          </p>
        </div>
        <Button asChild>
          <Link href="/evaluation/datasets/new">
            <Plus className="mr-2 h-4 w-4" />
            Create Dataset
          </Link>
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
          <p className="mt-4 text-muted-foreground">Loading datasets...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && datasets.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground opacity-50" />
            <h3 className="mt-4 text-lg font-semibold">No datasets yet</h3>
            <p className="mt-2 text-sm text-muted-foreground text-center max-w-sm">
              Create your first test dataset with ground truth queries to start evaluating your RAG system
            </p>
            <Button asChild className="mt-6">
              <Link href="/evaluation/datasets/new">
                <Plus className="mr-2 h-4 w-4" />
                Create Your First Dataset
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Datasets Grid */}
      {!isLoading && datasets.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset) => (
            <Card key={dataset.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1 flex-1">
                    <CardTitle className="line-clamp-1">{dataset.name}</CardTitle>
                    <CardDescription className="line-clamp-2">
                      {dataset.description || "No description"}
                    </CardDescription>
                  </div>
                  <Badge variant="secondary" className="ml-2">
                    {dataset.query_count} {dataset.query_count === 1 ? "query" : "queries"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="text-xs text-muted-foreground">
                    Created {new Date(dataset.created_at).toLocaleDateString()}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/evaluation/datasets/${dataset.id}`)}
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(dataset.id)}
                      disabled={deleting === dataset.id}
                    >
                      {deleting === dataset.id ? (
                        <div className="h-3 w-3 animate-spin rounded-full border-2 border-solid border-current border-r-transparent" />
                      ) : (
                        <Trash2 className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
