"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Search, AlertCircle, FileText } from "lucide-react";
import { ragServiceClient } from "@/lib/api";
import type { RetrievalMethod, QueryResponse } from "@/lib/types";

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [retrievalMethod, setRetrievalMethod] = useState<RetrievalMethod>("basic");
  const [topK, setTopK] = useState<number>(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<QueryResponse | null>(null);

  const handleSubmit = async () => {
    if (!query.trim()) {
      setError("Please enter a query");
      return;
    }

    if (topK < 1 || topK > 20) {
      setError("Top K must be between 1 and 20");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const response = await ragServiceClient.query({
        query: query.trim(),
        retrieval_method: retrievalMethod,
        top_k: topK,
      });
      setResults(response);
    } catch (err: any) {
      setError(err.message || "Failed to execute query");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Query Interface</h1>
        <p className="text-muted-foreground">
          Test RAG queries with different retrieval methods
        </p>
      </div>

      {/* Query Form */}
      <Card>
        <CardHeader>
          <CardTitle>Query Configuration</CardTitle>
          <CardDescription>Enter your query and select retrieval settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Query Input */}
          <div className="space-y-2">
            <Label htmlFor="query">
              Query <span className="text-destructive">*</span>
            </Label>
            <Input
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter your question or search query..."
              className="text-base"
            />
            <p className="text-xs text-muted-foreground">
              Press Enter to submit or Shift+Enter for new line
            </p>
          </div>

          {/* Retrieval Method */}
          <div className="space-y-2">
            <Label>Retrieval Method</Label>
            <div className="grid gap-3 md:grid-cols-3">
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
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium capitalize">
                        {method.replace("-", " ")}
                      </span>
                      {retrievalMethod === method && (
                        <Badge variant="default" className="text-xs">
                          Selected
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {method === "basic" && "Standard vector similarity"}
                      {method === "multi-query" && "Multiple query variations"}
                      {method === "hybrid" && "Vector + keyword search"}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Top K */}
          <div className="space-y-2">
            <Label htmlFor="top-k">Top K Documents</Label>
            <Input
              id="top-k"
              type="number"
              min="1"
              max="20"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-32"
            />
            <p className="text-xs text-muted-foreground">
              Number of documents to retrieve (1-20)
            </p>
          </div>

          {/* Submit Button */}
          <Button onClick={handleSubmit} disabled={loading || !query.trim()} size="lg">
            {loading ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent" />
                Searching...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Search
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-4">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              Search Results ({results.documents.length} documents)
            </h2>
            <div className="flex items-center gap-2">
              <Badge variant="outline">Method: {results.search_type_used}</Badge>
              {results.processing_time_ms && (
                <Badge variant="outline">{results.processing_time_ms}ms</Badge>
              )}
            </div>
          </div>

          {/* Empty Results */}
          {results.documents.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground opacity-50" />
                <p className="mt-4 text-muted-foreground">No documents found</p>
              </CardContent>
            </Card>
          )}

          {/* Document Results */}
          {results.documents.length > 0 && (
            <div className="space-y-3">
              {results.documents.map((doc, index) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="secondary">#{index + 1}</Badge>
                        </div>
                        {doc.metadata?.source ? (
                          <div className="text-sm text-muted-foreground">
                            Source: {String(doc.metadata.source)}
                          </div>
                        ) : null}
                      </div>
                      <Badge variant="outline">Score: {doc.relevance_score.toFixed(3)}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed">{doc.content}</p>
                    {doc.metadata && Object.keys(doc.metadata).length > 1 && (
                      <div className="mt-3 pt-3 border-t">
                        <p className="text-xs text-muted-foreground mb-2">Metadata:</p>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(doc.metadata)
                            .filter(([key]) => key !== "source")
                            .map(([key, value]) => (
                              <Badge key={key} variant="outline" className="text-xs">
                                {key}: {String(value)}
                              </Badge>
                            ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Info Card */}
      {!results && (
        <Card>
          <CardHeader>
            <CardTitle>How to use</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
              <li>Enter your question or search query in the text field</li>
              <li>Select a retrieval method (basic, multi-query, or hybrid)</li>
              <li>Choose how many documents to retrieve (top K)</li>
              <li>Click Search or press Enter to see results</li>
              <li>View retrieved documents with relevance scores and metadata</li>
            </ol>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
