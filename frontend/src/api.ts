import { useEffect, useState } from "react";

export type DependencyStatus = "ok" | "missing" | "failed" | "not_available" | "not_configured";

export interface Health {
  status: string;
  version: string;
  environment: string;
  dependencies: { name: string; status: DependencyStatus; detail: string }[];
}

export interface FileSummary {
  rows: number;
  label_counts: Record<"0" | "1", number>;
  timestamp_min: string;
  timestamp_max: string;
  malformed_rows: number;
  duplicate_transaction_id_rows: number;
  out_of_order_rows: number;
}

export interface DatasetValidation {
  archive_sha256: string;
  passed: boolean;
  train_ends_before_test: boolean;
  warnings: string[];
  columns: number;
  files: Record<string, FileSummary>;
}

export interface ActiveSettings {
  version: string;
  settings: { key: string; value: string; description: string }[];
}

type Result<T> = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: T };

/** Fetch a backend endpoint once. Errors carry the API's `detail` message when it has one. */
export function useApi<T>(path: string): Result<T> {
  const [result, setResult] = useState<Result<T>>({ state: "loading" });
  useEffect(() => {
    let active = true;
    fetch(`/api${path}`)
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail ?? `Request failed with status ${response.status}.`);
        return body as T;
      })
      .then((data) => active && setResult({ state: "ready", data }))
      .catch((error: Error) =>
        active &&
        setResult({
          state: "error",
          message: error instanceof TypeError ? "Cannot reach the backend. Is it running on port 8000?" : error.message,
        }),
      );
    return () => {
      active = false;
    };
  }, [path]);
  return result;
}
