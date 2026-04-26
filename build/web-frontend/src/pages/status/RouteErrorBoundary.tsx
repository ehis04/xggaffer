import { Component } from "react";
import type { ReactNode } from "react";
import { AppErrorPage } from "../../pages/status/AppErrorPage";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: unknown;
}

const INITIAL_STATE: State = { hasError: false, error: undefined };

export class RouteErrorBoundary extends Component<Props, State> {
  state: State = INITIAL_STATE;

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, error };
  }

  componentDidCatch(): void {}

  render() {
    if (this.state.hasError) {
      return (
        <AppErrorPage
          error={this.state.error}
          onReset={() => this.setState(INITIAL_STATE)}
        />
      );
    }
    return this.props.children;
  }
}