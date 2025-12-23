"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { AlertCircle, BarChart3, CheckCircle, Clock } from "lucide-react";
import { useEvaluationStore } from "@/lib/stores";

function ResultsContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job");

  const { jobs, currentResults, fetchJob, fetchResults, startPolling, stopPolling } = useEvaluationStore();
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);

  const job = jobId ? jobs.find((j) => j.job_id === jobId) : null;

  useEffect(() => {
    setMounted(true);

    if (jobId) {
      const loadJob = async () => {
        try {
          await fetchJob(jobId);

          // Start polling if job is not complete
          const currentJob = jobs.find((j) => j.job_id === jobId);
          if (currentJob && (currentJob.status === "queued" || currentJob.status === "running")) {
            startPolling(jobId);
          } else if (currentJob?.status === "completed") {
            await fetchResults(jobId);
          }
        } catch (err) {
          console.error("Failed to load job:", err);
        } finally {
          setLoading(false);
        }
      };

      loadJob();
    } else {
      setLoading(false);
    }

    return () => {
      if (jobId) {
        stopPolling(jobId);
      }
    };
  }, [jobId, fetchJob, fetchResults, startPolling, stopPolling, jobs]);

  if (!mounted) {
    return null;
  }

  if (!jobId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Evaluation Results</h1>
          <p className="text-muted-foreground">
            View and analyze evaluation metrics and results
          </p>
        </div>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No job ID specified. Please select a job from the dashboard or evaluation runner.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (loading && !job) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
        <p className="ml-4 text-muted-foreground">Loading job...</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Evaluation Results</h1>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Job not found</AlertDescription>
        </Alert>
      </div>
    );
  }

  const statusIcon = {
    queued: <Clock className="h-5 w-5" />,
    running: (
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-solid border-current border-r-transparent" />
    ),
    completed: <CheckCircle className="h-5 w-5 text-green-500" />,
    failed: <AlertCircle className="h-5 w-5 text-destructive" />,
  };

  const statusVariant = {
    queued: "secondary" as const,
    running: "default" as const,
    completed: "default" as const,
    failed: "destructive" as const,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Evaluation Results</h1>
        <p className="text-muted-foreground">Job ID: {job.job_id}</p>
      </div>

      {/* Job Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle>Job Status</CardTitle>
              <CardDescription>
                Retrieval Method: {job.retrieval_method} | K Values: [{job.k_values.join(", ")}]
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {statusIcon[job.status]}
              <Badge variant={statusVariant[job.status]}>{job.status}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {job.status === "running" && job.progress !== undefined && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Progress</span>
                <span>{job.progress}%</span>
              </div>
              <Progress value={job.progress} />
            </div>
          )}

          {job.status === "failed" && job.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{job.error}</AlertDescription>
            </Alert>
          )}

          {job.status === "completed" && (
            <div className="text-sm text-muted-foreground">
              <p>Started: {job.started_at && new Date(job.started_at).toLocaleString()}</p>
              <p>Completed: {job.completed_at && new Date(job.completed_at).toLocaleString()}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {job.status === "completed" && currentResults && (
        <>
          {/* Aggregate Metrics */}
          <div>
            <h2 className="text-xl font-bold mb-4">Aggregate Metrics</h2>
            <div className="grid gap-4 md:grid-cols-3">
              {/* NDCG Card */}
              <Card>
                <CardHeader>
                  <CardTitle>NDCG</CardTitle>
                  <CardDescription>Normalized Discounted Cumulative Gain</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(currentResults.aggregate_metrics.ndcg).map(([k, value]) => (
                      <div key={k} className="flex items-center justify-between">
                        <span className="text-sm">@{k}</span>
                        <span className="text-lg font-bold">{value.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* MAP Card */}
              <Card>
                <CardHeader>
                  <CardTitle>MAP</CardTitle>
                  <CardDescription>Mean Average Precision</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(currentResults.aggregate_metrics.map).map(([k, value]) => (
                      <div key={k} className="flex items-center justify-between">
                        <span className="text-sm">@{k}</span>
                        <span className="text-lg font-bold">{value.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* MRR Card */}
              <Card>
                <CardHeader>
                  <CardTitle>MRR</CardTitle>
                  <CardDescription>Mean Reciprocal Rank</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(currentResults.aggregate_metrics.mrr).map(([k, value]) => (
                      <div key={k} className="flex items-center justify-between">
                        <span className="text-sm">@{k}</span>
                        <span className="text-lg font-bold">{value.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Chart Placeholder */}
          <Card>
            <CardHeader>
              <CardTitle>Metrics Visualization</CardTitle>
              <CardDescription>
                Charts will be displayed here when Recharts is installed
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-12 bg-muted/20 rounded-lg">
                <div className="text-center">
                  <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <p className="text-muted-foreground">
                    Install Recharts in Docker to see metrics visualizations
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Per-Query Results */}
          <Card>
            <CardHeader>
              <CardTitle>Per-Query Results</CardTitle>
              <CardDescription>
                Individual query performance ({currentResults.per_query_metrics.length} queries)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {currentResults.per_query_metrics.slice(0, 5).map((result, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="font-medium mb-2">{result.query}</div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">NDCG:</span>{" "}
                        {Object.entries(result.ndcg)
                          .map(([k, v]) => `@${k}: ${v.toFixed(3)}`)
                          .join(", ")}
                      </div>
                      <div>
                        <span className="text-muted-foreground">MAP:</span>{" "}
                        {Object.entries(result.map)
                          .map(([k, v]) => `@${k}: ${v.toFixed(3)}`)
                          .join(", ")}
                      </div>
                      <div>
                        <span className="text-muted-foreground">MRR:</span>{" "}
                        {Object.entries(result.mrr)
                          .map(([k, v]) => `@${k}: ${v.toFixed(3)}`)
                          .join(", ")}
                      </div>
                    </div>
                  </div>
                ))}
                {currentResults.per_query_metrics.length > 5 && (
                  <p className="text-sm text-muted-foreground text-center">
                    Showing 5 of {currentResults.per_query_metrics.length} queries
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Waiting Message */}
      {(job.status === "queued" || job.status === "running") && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {job.status === "queued" ? "Job Queued" : "Evaluation Running"}
            </h3>
            <p className="text-sm text-muted-foreground text-center max-w-md">
              Your evaluation job is {job.status}. This page will automatically update when
              results are available.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center">
              <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4 animate-pulse" />
              <p className="text-muted-foreground">Loading results...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    }>
      <ResultsContent />
    </Suspense>
  );
}
