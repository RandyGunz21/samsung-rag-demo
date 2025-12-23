"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PlayCircle, AlertCircle, Check } from "lucide-react";
import { useEvaluationStore } from "@/lib/stores";
import type { RetrievalMethod } from "@/lib/types";

export default function RunEvaluationPage() {
  const router = useRouter();
  const { datasets, fetchDatasets, submitEvaluation, startPolling, isLoading } = useEvaluationStore();

  const [mounted, setMounted] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [retrievalMethod, setRetrievalMethod] = useState<RetrievalMethod>("basic");
  const [kValues, setKValues] = useState<string>("3,5,10");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    fetchDatasets();
  }, [fetchDatasets]);

  const parseKValues = (input: string): number[] => {
    return input
      .split(",")
      .map((v) => parseInt(v.trim()))
      .filter((v) => !isNaN(v) && v > 0);
  };

  const validate = (): boolean => {
    setError(null);

    if (!selectedDataset) {
      setError("Please select a test dataset");
      return false;
    }

    const parsed = parseKValues(kValues);
    if (parsed.length === 0) {
      setError("Please enter valid k values (e.g., 3,5,10)");
      return false;
    }

    return true;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      return;
    }

    setSubmitting(true);
    try {
      const parsed = parseKValues(kValues);
      const jobId = await submitEvaluation({
        dataset_id: selectedDataset,
        retrieval_method: retrievalMethod,
        k_values: parsed,
      });

      setJobId(jobId);
      setSubmitted(true);

      // Start polling for job status
      startPolling(jobId);
    } catch (err: any) {
      setError(err.message || "Failed to submit evaluation");
    } finally {
      setSubmitting(false);
    }
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Run Evaluation</h1>
        <p className="text-muted-foreground">
          Submit evaluation jobs to test retrieval methods
        </p>
      </div>

      {/* Success Message */}
      {submitted && jobId && (
        <Alert>
          <Check className="h-4 w-4" />
          <AlertDescription>
            Evaluation job submitted successfully! Job ID: {jobId}
            <Button
              variant="link"
              className="ml-2"
              onClick={() => router.push(`/evaluation/results?job=${jobId}`)}
            >
              View Results
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Configuration Form */}
      <Card>
        <CardHeader>
          <CardTitle>Evaluation Configuration</CardTitle>
          <CardDescription>
            Select dataset and configure evaluation parameters
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Dataset Selection */}
          <div className="space-y-2">
            <Label htmlFor="dataset">
              Test Dataset <span className="text-destructive">*</span>
            </Label>
            {isLoading ? (
              <div className="text-sm text-muted-foreground">Loading datasets...</div>
            ) : datasets.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                No datasets available.{" "}
                <Button
                  variant="link"
                  className="p-0 h-auto"
                  onClick={() => router.push("/evaluation/datasets/new")}
                >
                  Create one first
                </Button>
              </div>
            ) : (
              <select
                id="dataset"
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">Select a dataset...</option>
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name} ({dataset.query_count} queries)
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Retrieval Method */}
          <div className="space-y-2">
            <Label>
              Retrieval Method <span className="text-destructive">*</span>
            </Label>
            <div className="grid gap-4 md:grid-cols-3">
              {(["basic", "multi-query", "hybrid"] as const).map((method) => (
                <Card
                  key={method}
                  className={`cursor-pointer transition-colors ${
                    retrievalMethod === method
                      ? "border-primary bg-accent"
                      : "hover:border-muted-foreground"
                  }`}
                  onClick={() => setRetrievalMethod(method)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base capitalize">
                        {method.replace("-", " ")}
                      </CardTitle>
                      {retrievalMethod === method && (
                        <Badge variant="default">Selected</Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">
                      {method === "basic" && "Standard vector similarity retrieval"}
                      {method === "multi-query" && "Generate multiple query variations"}
                      {method === "hybrid" && "Combine vector and keyword search"}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* K Values */}
          <div className="space-y-2">
            <Label htmlFor="k-values">
              K Values <span className="text-destructive">*</span>
            </Label>
            <Input
              id="k-values"
              value={kValues}
              onChange={(e) => setKValues(e.target.value)}
              placeholder="e.g., 3,5,10"
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated list of k values (top-k documents to retrieve)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleSubmit}
          disabled={submitting || isLoading || datasets.length === 0}
          size="lg"
        >
          {submitting ? (
            <>
              <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent" />
              Submitting...
            </>
          ) : (
            <>
              <PlayCircle className="mr-2 h-4 w-4" />
              Run Evaluation
            </>
          )}
        </Button>
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>What happens next?</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
            <li>Your evaluation job will be queued and processed by the backend</li>
            <li>The system will run your test queries using the selected retrieval method</li>
            <li>Retrieved documents will be compared against ground truth</li>
            <li>Metrics (NDCG, MAP, MRR) will be calculated for each k value</li>
            <li>Results will be available in the Results page once complete</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
