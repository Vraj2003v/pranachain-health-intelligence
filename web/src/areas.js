export const AREAS = [
  { scenario: "Cardiovascular / hypertension", icon: "🩺", title: "Cardiovascular", short: "Cardiovascular", sub: "Blood pressure, heart rate, HRV, steps, LDL", hue: "#b03a48",
    measures: ["sbp", "dbp", "rhr", "hrv", "steps"], watches: "Blood pressure, resting heart rate, HRV, steps and LDL cholesterol",
    why: "Changes in these measures can matter for heart and blood-vessel health, so they are worth discussing with a healthcare provider alongside your history.",
    calm: "Your blood pressure and heart readings stayed within your own usual range." },
  { scenario: "Metabolic health", icon: "⚖️", title: "Metabolic", short: "Metabolic", sub: "Weight, steps, sleep, HbA1c, glucose", hue: "#2f6fa8",
    measures: ["weight", "steps", "sleep"], watches: "Weight, activity, sleep, HbA1c and fasting glucose",
    why: "Shifts in these measures can relate to how the body handles blood sugar and weight, so they are worth discussing with a healthcare provider alongside your history.",
    calm: "Your weight, activity and sleep stayed within your own usual range." },
  { scenario: "Women's health (PCOS)", icon: "🌸", title: "Women's health", short: "Women's health", sub: "Cycle length and regularity", hue: "#7a4fa3",
    measures: [], watches: "Cycle length and regularity, with related history",
    why: "Irregular cycle timing can relate to hormonal conditions, so it is worth discussing with a healthcare provider alongside your history.",
    calm: "Your cycle timing stayed within a typical range." },
];
