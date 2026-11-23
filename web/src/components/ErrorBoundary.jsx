import { Component } from "react";

// If a screen fails to draw, show a clear message and a way back instead of a blank page.
export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() { return { failed: true }; }

  componentDidCatch(error) { console.error("PranaPulse screen error:", error); }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="errscreen" role="alert">
        <h1>Something went wrong on this screen</h1>
        <p>Your files and results are safe. Reload the page to continue. If it happens again, tell the team what you were doing.</p>
        <button type="button" className="btn" onClick={() => window.location.reload()}>Reload the page</button>
      </div>
    );
  }
}
