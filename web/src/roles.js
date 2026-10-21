// What each account type sees. This shapes the interface only; data access is
// still limited to each user's own uploaded files on the server.
const LABEL = { summary: "My summary", ask: "Ask a question", timeline: "Trends", insights: "Full findings",
  coverage: "Data quality", explore: "Compare", cohort: "All patients", documents: "Files", audit: "Activity log" };

const VIEWS = {
  patient:    { home: "summary", tabs: ["summary", "ask", "timeline", "explore", "documents"], rail: false, labels: { documents: "My files" } },
  clinician:  { home: "cohort",  tabs: ["cohort", "summary", "ask", "timeline", "explore", "insights", "coverage", "documents"], rail: true, labels: { summary: "Patient summary" } },
  admin:      { home: "cohort",  tabs: ["cohort", "summary", "ask", "timeline", "explore", "insights", "coverage", "documents", "audit"], rail: true, labels: { summary: "Patient summary" } },
};

export const viewFor = (role) => {
  const v = VIEWS[role] || VIEWS.clinician   // unknown or retired roles get the provider view;
  return { ...v, tabList: v.tabs.map((k) => [k, v.labels[k] || LABEL[k]]) };
};
