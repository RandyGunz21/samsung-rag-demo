"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, Trash2, Save, AlertCircle, ArrowLeft } from "lucide-react";
import { useEvaluationStore } from "@/lib/stores";
import type { TestDataset, TestQuery, ExpectedDocument } from "@/lib/types";

interface GroundTruthEditorProps {
  dataset?: TestDataset;
  mode: "create" | "edit";
}

export function GroundTruthEditor({ dataset, mode }: GroundTruthEditorProps) {
  const router = useRouter();
  const { createDataset, updateDataset, isLoading, error } = useEvaluationStore();

  // Form state
  const [name, setName] = useState(dataset?.name || "");
  const [description, setDescription] = useState(dataset?.description || "");
  const [queries, setQueries] = useState<TestQuery[]>(
    dataset?.queries || [
      {
        query: "",
        expected_docs: [{ doc_id: "", relevance: 1.0 }],
      },
    ]
  );
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Query operations
  const addQuery = () => {
    setQueries([
      ...queries,
      {
        query: "",
        expected_docs: [{ doc_id: "", relevance: 1.0 }],
      },
    ]);
  };

  const removeQuery = (index: number) => {
    if (queries.length === 1) {
      setValidationError("Dataset must have at least one query");
      return;
    }
    setQueries(queries.filter((_, i) => i !== index));
  };

  const updateQuery = (index: number, field: keyof TestQuery, value: any) => {
    const newQueries = [...queries];
    newQueries[index] = { ...newQueries[index], [field]: value };
    setQueries(newQueries);
  };

  // Expected document operations
  const addExpectedDoc = (queryIndex: number) => {
    const newQueries = [...queries];
    newQueries[queryIndex].expected_docs.push({ doc_id: "", relevance: 1.0 });
    setQueries(newQueries);
  };

  const removeExpectedDoc = (queryIndex: number, docIndex: number) => {
    const newQueries = [...queries];
    if (newQueries[queryIndex].expected_docs.length === 1) {
      setValidationError("Query must have at least one expected document");
      return;
    }
    newQueries[queryIndex].expected_docs = newQueries[queryIndex].expected_docs.filter(
      (_, i) => i !== docIndex
    );
    setQueries(newQueries);
  };

  const updateExpectedDoc = (
    queryIndex: number,
    docIndex: number,
    field: keyof ExpectedDocument,
    value: any
  ) => {
    const newQueries = [...queries];
    newQueries[queryIndex].expected_docs[docIndex] = {
      ...newQueries[queryIndex].expected_docs[docIndex],
      [field]: value,
    };
    setQueries(newQueries);
  };

  // Validation
  const validate = (): boolean => {
    setValidationError(null);

    if (!name.trim()) {
      setValidationError("Dataset name is required");
      return false;
    }

    if (queries.length === 0) {
      setValidationError("Dataset must have at least one query");
      return false;
    }

    for (let i = 0; i < queries.length; i++) {
      const query = queries[i];

      if (!query.query.trim()) {
        setValidationError(`Query ${i + 1} text is required`);
        return false;
      }

      if (query.expected_docs.length === 0) {
        setValidationError(`Query ${i + 1} must have at least one expected document`);
        return false;
      }

      for (let j = 0; j < query.expected_docs.length; j++) {
        const doc = query.expected_docs[j];

        if (!doc.doc_id.trim()) {
          setValidationError(`Query ${i + 1}, Document ${j + 1}: Document ID is required`);
          return false;
        }

        if (doc.relevance < 0 || doc.relevance > 1) {
          setValidationError(`Query ${i + 1}, Document ${j + 1}: Relevance must be between 0 and 1`);
          return false;
        }
      }
    }

    return true;
  };

  // Save
  const handleSave = async () => {
    if (!validate()) {
      return;
    }

    setSaving(true);
    try {
      if (mode === "create") {
        const datasetId = await createDataset({
          name: name.trim(),
          description: description.trim() || undefined,
          queries,
        });
        router.push("/evaluation/datasets");
      } else if (dataset) {
        await updateDataset(dataset.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          queries,
        });
        router.push("/evaluation/datasets");
      }
    } catch (err) {
      console.error("Failed to save dataset:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {mode === "create" ? "Create Test Dataset" : "Edit Test Dataset"}
          </h1>
          <p className="text-muted-foreground">
            Define test queries and their expected relevant documents
          </p>
        </div>
        <Button variant="outline" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </div>

      {/* Error Alerts */}
      {(error || validationError) && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || validationError}</AlertDescription>
        </Alert>
      )}

      {/* Basic Info */}
      <Card>
        <CardHeader>
          <CardTitle>Dataset Information</CardTitle>
          <CardDescription>Basic information about the test dataset</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">
              Dataset Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Product Documentation Test Set"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description of this dataset"
            />
          </div>
        </CardContent>
      </Card>

      {/* Queries */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">Test Queries</h2>
            <p className="text-sm text-muted-foreground">
              Define queries and their expected relevant documents
            </p>
          </div>
          <Button onClick={addQuery}>
            <Plus className="mr-2 h-4 w-4" />
            Add Query
          </Button>
        </div>

        {queries.map((query, queryIndex) => (
          <Card key={queryIndex}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Query {queryIndex + 1}</CardTitle>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => removeQuery(queryIndex)}
                  disabled={queries.length === 1}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Query Text */}
              <div className="space-y-2">
                <Label htmlFor={`query-${queryIndex}`}>
                  Query Text <span className="text-destructive">*</span>
                </Label>
                <Input
                  id={`query-${queryIndex}`}
                  value={query.query}
                  onChange={(e) => updateQuery(queryIndex, "query", e.target.value)}
                  placeholder="Enter the test query"
                />
              </div>

              {/* Expected Documents */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Expected Documents <span className="text-destructive">*</span></Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => addExpectedDoc(queryIndex)}
                  >
                    <Plus className="mr-2 h-3 w-3" />
                    Add Document
                  </Button>
                </div>

                {query.expected_docs.map((doc, docIndex) => (
                  <div
                    key={docIndex}
                    className="flex items-center gap-2 p-3 border rounded-lg"
                  >
                    <div className="flex-1 space-y-2">
                      <Input
                        value={doc.doc_id}
                        onChange={(e) =>
                          updateExpectedDoc(queryIndex, docIndex, "doc_id", e.target.value)
                        }
                        placeholder="Document ID"
                      />
                    </div>
                    <div className="w-32 space-y-2">
                      <Input
                        type="number"
                        min="0"
                        max="1"
                        step="0.1"
                        value={doc.relevance}
                        onChange={(e) =>
                          updateExpectedDoc(
                            queryIndex,
                            docIndex,
                            "relevance",
                            parseFloat(e.target.value)
                          )
                        }
                        placeholder="Relevance"
                      />
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => removeExpectedDoc(queryIndex, docIndex)}
                      disabled={query.expected_docs.length === 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Save Button */}
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving || isLoading}>
          {saving || isLoading ? (
            <>
              <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Dataset
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
