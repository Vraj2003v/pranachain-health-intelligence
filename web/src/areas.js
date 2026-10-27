export const AREAS = [
  { scenario: "Cardiovascular / hypertension", icon: "🩺", title: "Heart and blood pressure", short: "Cardiovascular", hue: "#b03a48",
    measures: ["sbp", "dbp", "rhr", "hrv"], watches: "Blood pressure, resting heart rate, HRV and LDL cholesterol",
    why: "Changes in these measures can matter for heart and blood-vessel health, so they are worth discussing with a healthcare provider alongside your history.",
    calm: "Your blood pressure and heart readings stayed within your own usual range." },
  { scenario: "Metabolic health", icon: "⚖️", title: "Weight, sugar and activity", short: "Metabolic", hue: "#2f6fa8",
    measures: ["weight", "steps", "sleep"], watches: "Weight, activity, sleep, HbA1c and fasting glucose",
    why: "Shifts in these measures can relate to how the body handles blood sugar and weight, so they are worth discussing with a healthcare provider alongside your history.",
    calm: "Your weight, activity and sleep stayed within your own usual range." },
  { scenario: "Women's health (PCOS)", icon: "🌸", title: "Cycle and hormones", short: "Women's health", hue: "#7a4fa3",
    measures: [], watches: "Cycle length and regularity, with related history",
    why: "Irregular cycle timing can relate to hormonal conditions, so it is worth discussing with a healthcare provider alongside your history.",
    calm: "Your cycle timing stayed within a typical range." },
];
