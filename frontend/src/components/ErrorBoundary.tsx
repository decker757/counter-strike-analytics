import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches React rendering errors in child components.
 * If the chat panel crashes, the map keeps working.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div
            style={{
              padding: 12,
              color: "#ff9800",
              background: "rgba(20,20,30,0.95)",
              borderRadius: 6,
              fontSize: 12,
            }}
          >
            ⚠️ Component error: {this.state.error?.message || "Unknown error"}
          </div>
        )
      );
    }
    return this.props.children;
  }
}
