import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" role="alert">
          <h2>Something went wrong</h2>
          <p>An unexpected error occurred while rendering this view.</p>
          <div style={{ marginTop: "12px" }}>
            <button
              className="btn btn-secondary"
              onClick={() => window.location.reload()}
            >
              Reload page
            </button>
          </div>
          {this.state.error && (
            <details style={{ marginTop: "16px" }}>
              <summary>Error details</summary>
              <pre style={{ marginTop: "8px", overflowX: "auto" }}>
                {this.state.error.toString()}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
