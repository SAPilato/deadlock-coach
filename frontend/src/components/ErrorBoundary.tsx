import { Component, type ReactNode } from "react";
import { ErrorBox } from "./ui";

/** Shows a page error in place instead of a blank screen. Layout remounts it on every route change. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { error: unknown }> {
  state = { error: null as unknown };

  static getDerivedStateFromError(error: unknown) {
    return { error };
  }

  render() {
    return this.state.error ? <ErrorBox error={this.state.error} /> : this.props.children;
  }
}
