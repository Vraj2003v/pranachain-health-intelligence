// "Getting started" steps a person has completed, remembered in this browser only.
const KEY = "pranapulse.steps";
export const STEPS = [["area", "Open a health area"], ["chart", "Change a chart (measure, range or zoom)"], ["ask", "Ask the assistant a question"], ["theme", "Try light or dark mode"]];
export const getSteps = () => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } };
export const mark = (step) => {
  const now = getSteps();
  if (now.includes(step)) return;
  try { localStorage.setItem(KEY, JSON.stringify([...now, step])); } catch { /* storage may be blocked */ }
  window.dispatchEvent(new Event("pp-steps"));
};
