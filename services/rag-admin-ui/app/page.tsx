"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FlaskConical,
  Database,
  Search,
  Upload,
  BarChart3,
  PlayCircle,
  FileText,
  Activity,
} from "lucide-react";
import { useEvaluationStore } from "@/lib/stores";

export default function DashboardPage() {
  const { datasets, jobs, fetchDatasets } = useEvaluationStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchDatasets();
  }, [fetchDatasets]);

  if (!mounted) {
    return null;
  }

  const recentJobs = jobs.slice(0, 5);
  const runningJobs = jobs.filter((j) => j.status === "running").length;
  const completedJobs = jobs.filter((j) => j.status === "completed").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your RAG system performance and activity
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Datasets</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{datasets.length}</div>
            <p className="text-xs text-muted-foreground">Test datasets available</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running Jobs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningJobs}</div>
            <p className="text-xs text-muted-foreground">Currently evaluating</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Jobs</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{completedJobs}</div>
            <p className="text-xs text-muted-foreground">Evaluation results ready</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
            <FlaskConical className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{jobs.length}</div>
            <p className="text-xs text-muted-foreground">All evaluation jobs</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="hover:bg-accent transition-colors cursor-pointer">
          <Link href="/evaluation/datasets">
            <CardHeader>
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                <CardTitle>Manage Datasets</CardTitle>
              </div>
              <CardDescription>
                Create and edit test datasets with ground truth
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-accent transition-colors cursor-pointer">
          <Link href="/evaluation/run">
            <CardHeader>
              <div className="flex items-center gap-2">
                <PlayCircle className="h-5 w-5" />
                <CardTitle>Run Evaluation</CardTitle>
              </div>
              <CardDescription>
                Test retrieval methods and compare performance
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-accent transition-colors cursor-pointer">
          <Link href="/evaluation/results">
            <CardHeader>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                <CardTitle>View Results</CardTitle>
              </div>
              <CardDescription>
                Analyze evaluation metrics and insights
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-accent transition-colors cursor-pointer">
          <Link href="/data/upload">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                <CardTitle>Upload Files</CardTitle>
              </div>
              <CardDescription>
                Add documents to your RAG knowledge base
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-accent transition-colors cursor-pointer">
          <Link href="/data/documents">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                <CardTitle>View Documents</CardTitle>
              </div>
              <CardDescription>Browse and manage indexed documents</CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:bg-accent transition-colors cursor-pointer">
          <Link href="/query">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                <CardTitle>Query Interface</CardTitle>
              </div>
              <CardDescription>Test RAG queries with different methods</CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Evaluation Jobs</CardTitle>
          <CardDescription>Latest evaluation activity and status</CardDescription>
        </CardHeader>
        <CardContent>
          {recentJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FlaskConical className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No evaluation jobs yet</p>
              <Button asChild className="mt-4" size="sm">
                <Link href="/evaluation/run">Run Your First Evaluation</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {recentJobs.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium">Job {job.job_id.slice(0, 8)}...</p>
                    <p className="text-xs text-muted-foreground">
                      Method: {job.retrieval_method} | K: [{job.k_values.join(", ")}]
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        job.status === "completed"
                          ? "default"
                          : job.status === "failed"
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {job.status}
                    </Badge>
                    {job.status === "completed" && (
                      <Button asChild variant="outline" size="sm">
                        <Link href={`/evaluation/results?job=${job.job_id}`}>
                          View Results
                        </Link>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
